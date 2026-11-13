// Talk to an NPC in the game (mod spec what/talk.md). The rule numbers below are from that file.
module Genpc

import RedHttpClient.*
import RedData.Json.*
import Audioware.*
import Codeware.UI.*

enum GenpcState {
  Idle = 0,
  Checking = 1,
  Waiting = 2,
  Showing = 3,
  Stuck = 4,
}

public class GenpcTick extends DelayCallback {
  public let owner: wref<GenpcSystem>;
  public let gen: Int32;
  public func Call() -> Void {
    if IsDefined(this.owner) {
      this.owner.OnTick(this.gen);
    }
  }
}

public class GenpcTimeout extends DelayCallback {
  public let owner: wref<GenpcSystem>;
  public let token: Int32;
  public func Call() -> Void {
    if IsDefined(this.owner) {
      this.owner.OnTimeout(this.token);
    }
  }
}

public class GenpcSystem extends ScriptableSystem {
  private let settings: ref<GenpcSettings>;
  private let panel: ref<GenpcPanel>;
  private let popup: ref<GenpcTypePopup>;
  private let typing: Bool;
  private let state: GenpcState;

  // Each request gets its own number. Only the answer to the newest request counts (rules 25, 28a).
  private let nextId: Int32;
  private let pending: Int32;
  private let voiceId: Int32;
  private let lastTurn: Int64;
  private let timeout: DelayID;
  private let timeoutToken: Int32;
  private let tickGen: Int32;

  private let target: wref<NPCPuppet>;
  private let targetEntity: EntityID;
  private let npcName: String;
  private let npcId: String;
  private let sessionId: Int64;
  private let choices: array<String>;
  private let lastTown: String;
  private let audioSlots: Int64;
  private let emitters: array<EntityID>;
  private let savedHubs: Variant;
  private let hubsHidden: Bool;
  private let weaponsBlocked: Bool;
  private let menuListener: ref<CallbackHandle>;
  private let lastRefused: EntityID;

  private func OnAttach() -> Void {
    this.settings = new GenpcSettings();
    ModSettings.RegisterListenerToClass(this.settings);
    this.panel = new GenpcPanel();
    this.pending = -1;
    this.lastTown = "watson";
    let callbacks = GameInstance.GetCallbackSystem();
    callbacks.RegisterCallback(n"Input/Key", this, n"OnKey");
    callbacks.RegisterCallback(n"Session/Ready", this, n"OnSessionReady");
    callbacks.RegisterCallback(n"Session/BeforeSave", this, n"OnBeforeSave");
    callbacks.RegisterCallback(n"Session/Pause", this, n"OnPause");
    callbacks.RegisterCallback(n"Session/BeforeEnd", this, n"OnSessionEnd");
    FTLog("[genpc] loaded");
  }

  private func OnDetach() -> Void {
    this.Close("detach");
    let callbacks = GameInstance.GetCallbackSystem();
    callbacks.UnregisterCallback(n"Input/Key", this, n"OnKey");
    callbacks.UnregisterCallback(n"Session/Ready", this);
    callbacks.UnregisterCallback(n"Session/BeforeSave", this);
    callbacks.UnregisterCallback(n"Session/Pause", this);
    callbacks.UnregisterCallback(n"Session/BeforeEnd", this);
    ModSettings.UnregisterListenerToClass(this.settings);
  }

  private func Base() -> String {
    return "http://localhost:8000";
  }

  public func IsPanelOpen() -> Bool {
    return NotEquals(this.state, GenpcState.Idle) && NotEquals(this.state, GenpcState.Checking);
  }

  // ---- Start (rules 1-4) ----

  private cb func OnSessionReady(evt: ref<GameSessionEvent>) {
    this.ResetTalk();
    this.lastTown = "watson";  // rule 13b
    // A save can hold the mod's weapon block. Always remove it after a load.
    let player = GetPlayer(this.GetGameInstance());
    if IsDefined(player) {
      StatusEffectHelper.RemoveStatusEffect(player, t"Genpc.NoWeapons");
    }
    this.weaponsBlocked = false;
    this.hubsHidden = false;
    this.panel = new GenpcPanel();
    this.panel.Build();
    this.ListenToMenus();
    this.tickGen += 1;  // one timer only, also after many loads
    this.StartTick();
    this.Post("/api/session/start", new JsonObject(), n"OnLoadStart", this.NewId());
  }

  private cb func OnBeforeSave(evt: ref<GameSessionEvent>) {
    this.Close("save");  // no weapon block and no hidden choices go into a save
  }

  private cb func OnPause(evt: ref<GameSessionEvent>) {
    if !this.typing {
      this.Close("pause");  // rule 24
    }
  }

  private cb func OnSessionEnd(evt: ref<GameSessionEvent>) {
    this.Close("load");  // rule 24
    let audio = GameInstance.GetAudioSystemExt(this.GetGameInstance());
    for id in this.emitters {
      audio.UnregisterEmitter(id, n"genpc");
    }
    ArrayClear(this.emitters);
    if IsDefined(this.menuListener) {
      this.UiSystem().UnregisterListenerBool(GetAllBlackboardDefs().UI_System.IsInMenu, this.menuListener);
      this.menuListener = null;
    }
  }

  private cb func OnLoadStart(response: ref<HttpResponse>, data: array<Variant>) {
    let answer = this.Answer(response, "session start (load)");
    if !IsDefined(answer) {
      return;
    }
    this.ReadStart(answer);
    // Rules 1, 1a: always send the world after a load. The engine keeps the memories.
    this.Post("/api/world", ParseJson(GenpcWorldJson()), n"OnLoadWorld", this.NewId());
  }

  private cb func OnLoadWorld(response: ref<HttpResponse>, data: array<Variant>) {
    this.Answer(response, "world (load)");
  }

  private func ReadStart(answer: ref<JsonObject>) -> Void {
    let caps = answer.GetKey("capabilities") as JsonObject;
    this.audioSlots = IsDefined(caps) ? caps.GetKeyInt64("audio_slots") : 0l;
    // Rule 4.
    FTLog(s"[genpc] engine: world \(answer.GetKeyString("world")), audio_slots \(this.audioSlots), llm \(answer.GetKeyString("llm"))");
    if this.audioSlots != 0l && this.audioSlots != 4l {
      FTLog(s"[genpc] audio_slots is \(this.audioSlots), not 4: no voice (rule 17b)");
    }
  }

  // ---- Menus (rule 24) ----

  private func UiSystem() -> ref<IBlackboard> {
    return GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(GetAllBlackboardDefs().UI_System);
  }

  private func InMenu() -> Bool {
    return this.UiSystem().GetBool(GetAllBlackboardDefs().UI_System.IsInMenu);
  }

  private func ListenToMenus() -> Void {
    if !IsDefined(this.menuListener) {
      this.menuListener = this.UiSystem().RegisterListenerBool(GetAllBlackboardDefs().UI_System.IsInMenu, this, n"OnMenu");
    }
  }

  protected cb func OnMenu(value: Bool) -> Bool {
    if value && !this.typing {
      this.Close("menu");
    }
    return true;
  }

  // ---- Keys ----

  private cb func OnKey(evt: ref<KeyInputEvent>) {
    if NotEquals(evt.GetAction(), EInputAction.IACT_Release) {
      return;
    }
    let key = evt.GetKey();
    if this.typing {
      // Rule 20a: all keys go into the text box. Only Enter does something here.
      if Equals(key, EInputKey.IK_Enter) {
        this.SendTyped();
      }
      return;
    }
    if this.InMenu() {
      return;  // keys in a menu are for the menu
    }
    if Equals(key, this.settings.Key()) {
      if Equals(this.state, GenpcState.Idle) {
        this.TryOpen();  // rule 5: on release
      } else {
        if this.IsPanelOpen() {
          this.Close("talk key");  // rule 24
        }
      }
      return;
    }
    if !Equals(this.state, GenpcState.Showing) {
      return;
    }
    if Equals(key, EInputKey.IK_1) {
      this.Choose(0);
    } else {
      if Equals(key, EInputKey.IK_2) {
        this.Choose(1);
      } else {
        if Equals(key, EInputKey.IK_3) {
          this.Choose(2);
        } else {
          if Equals(key, EInputKey.IK_Enter) {
            this.StartTyping();
          }
        }
      }
    }
  }

  // ---- Open (rules 5-14) ----

  private func TryOpen() -> Void {
    let game = this.GetGameInstance();
    let player = GetPlayer(game);
    if !IsDefined(player) {
      return;
    }
    let npc = GameInstance.GetTargetingSystem(game).GetLookAtObject(player, false, false) as NPCPuppet;
    if !IsDefined(npc) {
      return;  // rule 8
    }
    let name = GenpcNpc.Name(npc);
    let note = this.Refusal(npc, player, name);
    if NotEquals(note, "-") {
      if StrLen(note) > 0 {
        this.Note(note);
      }
      return;
    }
    if !this.panel.IsBuilt() {
      this.panel.Build();
      if !this.panel.IsBuilt() {
        FTLog("[genpc] the panel cannot open: no HUD");
        return;
      }
    }
    this.target = npc;
    this.targetEntity = npc.GetEntityID();
    this.npcName = name;
    this.state = GenpcState.Checking;
    // Rule 2: ask the engine before each greeting. It must answer in 3 seconds (rule 3).
    this.Post("/api/session/start", new JsonObject(), n"OnTalkStart", this.Expect());
    this.StartTimeout(3.0);
  }

  // Rule 7: "-" = the panel can open, "" = no note, else the note.
  private func Refusal(npc: ref<NPCPuppet>, player: ref<PlayerPuppet>, name: String) -> String {
    switch this.RefusalWhy(npc, player, name) {
      case "-": return "-";
      case "down": return "";
      case "far": return "Move closer.";
      case "story": return "This person does not want to talk.";
      default: return "Not now.";
    }
  }

  // The exact reason for rule 7, for the log. "-" if the player can talk.
  private func RefusalWhy(npc: ref<NPCPuppet>, player: ref<PlayerPuppet>, name: String) -> String {
    let game = this.GetGameInstance();
    if GenpcNpc.IsDown(npc) {
      return "down";
    }
    if GenpcNpc.Distance(npc, player) > 4.0 {
      return "far";
    }
    if npc.IsHostile() {
      return "hostile";
    }
    if player.IsInCombat() {
      return "combat";
    }
    if VehicleComponent.IsMountedToVehicle(game, player) {
      return "vehicle";
    }
    let scenes = GameInstance.GetSceneSystem(game).GetScriptInterface();
    if scenes.IsEntityInScene(npc.GetEntityID()) {
      return "scene";
    }
    if scenes.IsEntityInDialogue(npc.GetEntityID()) {
      return "dialogue";
    }
    if GenpcNpc.IsStoryCharacter(name) {
      return "story";
    }
    return "-";
  }

  // Log why an NPC near the player cannot talk, once for each NPC (so a test shows the cause).
  private func LogRefusal(npc: ref<NPCPuppet>, player: ref<PlayerPuppet>, name: String) -> Void {
    let why = this.RefusalWhy(npc, player, name);
    // "far" and "down" are normal (bodies after a fight filled the 2nd test log).
    if Equals(why, "-") || Equals(why, "far") || Equals(why, "down") || Equals(npc.GetEntityID(), this.lastRefused) {
      return;
    }
    this.lastRefused = npc.GetEntityID();
    FTLog(s"[genpc] cannot talk to \(name) (record \(GenpcNpc.RecordId(npc)), shown name \"\(npc.GetDisplayName())\"): \(why)");
  }

  private cb func OnTalkStart(response: ref<HttpResponse>, data: array<Variant>) {
    let answer = this.Answer(response, "session start");
    if !this.IsCurrent(data, GenpcState.Checking) {
      return;
    }
    this.StopTimeout();
    if !IsDefined(answer) {
      this.ResetTalk();
      if IsDefined(response) {
        this.Note(s"The engine had a problem (code \(response.GetStatusCode())).");  // rule 28b
      } else {
        this.Note("The engine does not run. Start it, then try again.");  // rule 7
      }
      return;
    }
    this.ReadStart(answer);
    // Rule 15: the panel opens after the engine answered.
    this.OpenPanel();
    this.StartTimeout(60.0);
    if NotEquals(answer.GetKeyString("world"), "cyberpunk") {
      // Rule 2a: the engine started again during play.
      this.Post("/api/world", ParseJson(GenpcWorldJson()), n"OnTalkWorld", this.Expect());
    } else {
      this.SendNpc();
    }
  }

  private cb func OnTalkWorld(response: ref<HttpResponse>, data: array<Variant>) {
    let answer = this.Answer(response, "world");
    if !this.IsCurrent(data, GenpcState.Waiting) {
      return;
    }
    if IsDefined(answer) {
      this.SendNpc();
    } else {
      this.Problem(response);
    }
  }

  // Rules 9-14.
  private func SendNpc() -> Void {
    let npc = this.target;
    if !IsDefined(npc) {
      this.Close("NPC gone");
      return;
    }
    let body = new JsonObject();
    let cast = GenpcNpc.CastId(this.npcName);
    let record = GenpcNpc.RecordId(npc);
    let entity = GenpcNpc.EntityDecimal(npc);
    FTLog(s"[genpc] NPC \(this.npcName): record \(record), entity \(entity), crowd \(npc.IsCrowd())");  // rule 14
    if StrLen(cast) > 0 {
      body.SetKeyString("record_id", cast);
    } else {
      if npc.IsCrowd() || StrLen(record) == 0 {
        body.SetKeyString("entity_id", entity);
      } else {
        body.SetKeyString("record_id", record);
      }
    }
    body.SetKeyString("name", this.npcName);
    let town = GenpcNpc.Town(this.GetGameInstance());
    if StrLen(town) > 0 {
      this.lastTown = town;
    }
    body.SetKeyString("settlement", this.lastTown);
    let gender = GenpcNpc.Gender(npc);
    if StrLen(gender) > 0 {
      body.SetKeyString("gender", gender);
    }
    this.Post("/api/npcs", body, n"OnNpc", this.Expect());
  }

  private cb func OnNpc(response: ref<HttpResponse>, data: array<Variant>) {
    let answer = this.Answer(response, "npcs");
    if !this.IsCurrent(data, GenpcState.Waiting) {
      return;
    }
    if !IsDefined(answer) {
      this.Problem(response);
      return;
    }
    this.npcId = answer.GetKeyString("npc_id");
    FTLog(s"[genpc] npc_id \(this.npcId), kind \(answer.GetKeyString("kind"))");
    let body = new JsonObject();
    body.SetKeyString("npc_id", this.npcId);
    this.Post("/api/dialog/open", body, n"OnLine", this.Expect());
  }

  // ---- Talk (rules 15-23) ----

  private func OpenPanel() -> Void {
    this.state = GenpcState.Waiting;
    this.panel.HideHint();
    this.panel.Open(this.npcName, this.settings.KeyLabel());
    this.BlockWeapons(true);  // rule 19a
    this.HideGameChoices();  // rule 23
  }

  private cb func OnLine(response: ref<HttpResponse>, data: array<Variant>) {
    let answer = this.Answer(response, "line");
    if !this.IsCurrent(data, GenpcState.Waiting) {
      return;  // rules 25, 28a: an old line does not show
    }
    this.StopTimeout();
    this.pending = -1;
    if !IsDefined(answer) {
      this.Problem(response);
      return;
    }
    this.sessionId = answer.GetKeyInt64("session_id");
    this.lastTurn = answer.GetKeyInt64("turn_id");
    ArrayClear(this.choices);
    let list = answer.GetKey("choices") as JsonArray;
    if IsDefined(list) {
      let i = 0u;
      while i < list.GetSize() && i < 3u {
        ArrayPush(this.choices, list.GetItemString(i));
        i += 1u;
      }
    }
    this.state = GenpcState.Showing;
    this.panel.ShowLine(answer.GetKeyString("npc_line"), this.choices);  // rules 16, 18
    this.AskVoice();
  }

  // Rules 17-17c.
  private func AskVoice() -> Void {
    if !this.settings.voiceOn || this.audioSlots != 4l {
      return;
    }
    this.voiceId = this.NewId();
    this.Post(s"/api/audio/\(this.lastTurn)/slot", new JsonObject(), n"OnVoice", this.voiceId);
  }

  private cb func OnVoice(response: ref<HttpResponse>, data: array<Variant>) {
    let answer = this.Answer(response, "voice");
    // Rule 25: no voice after the panel closed. Only the voice of the line on the panel plays.
    if ArraySize(data) == 0 || FromVariant<Int32>(data[0]) != this.voiceId || !Equals(this.state, GenpcState.Showing) {
      return;
    }
    if !IsDefined(answer) {
      return;  // rule 29: the line stays, without a voice
    }
    let slot = answer.GetKeyString("slot");
    let audio = GameInstance.GetAudioSystemExt(this.GetGameInstance());
    if !audio.IsRegisteredEmitter(this.targetEntity, n"genpc") {
      if !audio.RegisterEmitter(this.targetEntity, n"genpc") {
        FTLog("[genpc] voice: could not add a sound source to the NPC");
        return;
      }
      ArrayPush(this.emitters, this.targetEntity);
    }
    audio.PlayOnEmitter(StringToName(slot), this.targetEntity, n"genpc");
    FTLog(s"[genpc] voice: played \(slot)");
  }

  private func Choose(i: Int32) -> Void {
    if i >= ArraySize(this.choices) {
      return;
    }
    this.Say(this.choices[i]);  // rules 19, 19b
  }

  private func Say(text: String) -> Void {
    let body = new JsonObject();
    body.SetKeyString("npc_id", this.npcId);
    body.SetKeyInt64("session_id", this.sessionId);
    body.SetKeyString("text", text);
    this.state = GenpcState.Waiting;
    this.voiceId = -1;  // the voice of the old line does not play now
    this.panel.Wait();  // rule 21
    this.StartTimeout(60.0);
    this.Post("/api/dialog/choose", body, n"OnLine", this.Expect());
  }

  private func StartTyping() -> Void {
    let manager = CustomPopupManager.GetInstance();
    if !manager.IsInitialized() {
      FTLog("[genpc] text box: popup manager not ready");
      return;
    }
    this.popup = new GenpcTypePopup();
    this.popup.owner = this;
    manager.ShowPopup(this.popup);  // OnTypingOpened sets typing, only if the popup really opens
  }

  public func OnTypingOpened() -> Void {
    this.typing = true;
  }

  private func SendTyped() -> Void {
    let text = IsDefined(this.popup) ? this.popup.input.GetText() : "";
    this.StopTyping();
    // Rule 20b: empty or only spaces: send nothing.
    if StrLen(StrReplaceAll(text, " ", "")) == 0 || !Equals(this.state, GenpcState.Showing) {
      return;
    }
    this.Say(text);
  }

  private func StopTyping() -> Void {
    this.typing = false;
    if IsDefined(this.popup) {
      this.popup.Close();
    }
    this.popup = null;
  }

  public func OnTypingClosed() -> Void {
    // Rule 20d: Esc closes the text box. The panel stays open.
    this.typing = false;
    this.popup = null;
  }

  // ---- Close (rules 24-27) ----

  public func OnTick(gen: Int32) -> Void {
    if gen != this.tickGen {
      return;
    }
    let game = this.GetGameInstance();
    let player = GetPlayer(game);
    if IsDefined(player) {
      let town = GenpcNpc.Town(game);
      if StrLen(town) > 0 {
        this.lastTown = town;
      }
      if this.IsPanelOpen() {
        let reason = this.CloseReason(player);
        if StrLen(reason) > 0 {
          this.Close(reason);
        }
      } else {
        if Equals(this.state, GenpcState.Idle) {
          this.UpdateHint(player);
        }
      }
    }
    this.StartTick();
  }

  private func CloseReason(player: ref<PlayerPuppet>) -> String {
    let npc = this.target;
    let game = this.GetGameInstance();
    if !IsDefined(npc) || GenpcNpc.IsDown(npc) {
      return "NPC down";
    }
    if GenpcNpc.Distance(npc, player) > 8.0 {
      return "walked away";
    }
    if npc.IsHostile() || player.IsInCombat() {
      return "combat";
    }
    if VehicleComponent.IsMountedToVehicle(game, player) {
      return "vehicle";
    }
    if GameInstance.GetPhoneManager(game).IsPhoneCallActive() {
      return "phone call";
    }
    if !this.typing && this.InMenu() {
      return "menu";
    }
    return "";
  }

  // Rules 5b, 5d: the hint shows only if the panel can open.
  private func UpdateHint(player: ref<PlayerPuppet>) -> Void {
    let npc = GameInstance.GetTargetingSystem(this.GetGameInstance()).GetLookAtObject(player, false, false) as NPCPuppet;
    if IsDefined(npc) && Equals(this.Refusal(npc, player, GenpcNpc.Name(npc)), "-") {
      this.panel.ShowHint(this.settings.KeyLabel());
    } else {
      if IsDefined(npc) {
        this.LogRefusal(npc, player, GenpcNpc.Name(npc));
      }
      this.panel.HideHint();
    }
  }

  private func Close(reason: String) -> Void {
    if Equals(this.state, GenpcState.Idle) {
      return;
    }
    FTLog(s"[genpc] panel closed: \(reason)");
    this.StopTyping();
    this.StopTimeout();
    this.ResetTalk();
    this.panel.Close();
    this.BlockWeapons(false);
    this.ShowGameChoices(Equals(reason, "talk key") || Equals(reason, "menu") || Equals(reason, "pause") || Equals(reason, "phone call"));
  }

  private func ResetTalk() -> Void {
    this.state = GenpcState.Idle;
    this.pending = -1;  // rule 25: later answers are ignored
    this.voiceId = -1;
    this.target = null;
  }

  // ---- Errors (rules 28-29) ----

  public func OnTimeout(token: Int32) -> Void {
    if token != this.timeoutToken {
      return;
    }
    this.timeoutToken = -1;
    if Equals(this.state, GenpcState.Checking) {
      FTLog("[genpc] engine: no answer in 3 seconds");
      this.ResetTalk();
      this.Note("The engine does not run. Start it, then try again.");  // rule 3
      return;
    }
    if Equals(this.state, GenpcState.Waiting) {
      FTLog("[genpc] engine: no line in 60 seconds");
      this.state = GenpcState.Stuck;
      this.pending = -1;  // rule 28a: a late line does not show
      this.panel.ShowProblem("No answer.");  // rule 28
    }
  }

  private func Problem(response: ref<HttpResponse>) -> Void {
    this.StopTimeout();
    this.pending = -1;
    this.state = GenpcState.Stuck;
    let code = IsDefined(response) ? response.GetStatusCode() : 0;
    this.panel.ShowProblem(s"The engine had a problem (code \(code)).");  // rule 28b
  }

  // ---- Game helpers ----

  private func BlockWeapons(on: Bool) -> Void {
    let player = GetPlayer(this.GetGameInstance());
    if !IsDefined(player) || Equals(on, this.weaponsBlocked) {
      return;
    }
    if on {
      StatusEffectHelper.ApplyStatusEffect(player, t"Genpc.NoWeapons");
    } else {
      StatusEffectHelper.RemoveStatusEffect(player, t"Genpc.NoWeapons");
    }
    this.weaponsBlocked = on;
  }

  private func HideGameChoices() -> Void {
    let defs = GetAllBlackboardDefs().UIInteractions;
    let bb = GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(defs);
    this.savedHubs = bb.GetVariant(defs.DialogChoiceHubs);
    let empty: DialogChoiceHubs;
    bb.SetVariant(defs.DialogChoiceHubs, ToVariant(empty), true);
    this.hubsHidden = true;
  }

  // Restore the saved choices only if the player is still with the NPC. Else the game makes new ones.
  private func ShowGameChoices(restore: Bool) -> Void {
    if !this.hubsHidden {
      return;
    }
    this.hubsHidden = false;
    if restore {
      let defs = GetAllBlackboardDefs().UIInteractions;
      GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(defs).SetVariant(defs.DialogChoiceHubs, this.savedHubs, true);
    }
  }

  private func Note(text: String) -> Void {
    let msg: SimpleScreenMessage;
    msg.isShown = true;
    msg.duration = 4.0;
    msg.message = text;
    let defs = GetAllBlackboardDefs().UI_Notifications;
    GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(defs).SetVariant(defs.OnscreenMessage, ToVariant(msg), true);
  }

  // ---- HTTP helpers ----

  private func NewId() -> Int32 {
    this.nextId += 1;
    return this.nextId;
  }

  // The next request of the conversation. Only its answer counts.
  private func Expect() -> Int32 {
    this.pending = this.NewId();
    return this.pending;
  }

  private func IsCurrent(data: array<Variant>, state: GenpcState) -> Bool {
    if ArraySize(data) == 0 || this.pending <= 0 || FromVariant<Int32>(data[0]) != this.pending {
      FTLog("[genpc] an old answer: ignored");
      return false;
    }
    return Equals(this.state, state);
  }

  private func Post(path: String, body: ref<JsonVariant>, callback: CName, id: Int32) -> Void {
    FTLog(s"[genpc] POST \(path)");  // rule 31
    AsyncHttpClient.PostJson(HttpCallback.Create(this, callback, [ToVariant(id)]), this.Base() + path, body);
  }

  // The answer as a JSON object, or null for an error. Rule 31: each answer code goes to the game log.
  private func Answer(response: ref<HttpResponse>, what: String) -> ref<JsonObject> {
    if !IsDefined(response) {
      FTLog(s"[genpc] \(what): no answer");
      return null;
    }
    let code = response.GetStatusCode();
    FTLog(s"[genpc] \(what): \(code)");
    if code != 200 {
      return null;
    }
    let json = response.GetJson();
    if !IsDefined(json) || !json.IsObject() {
      FTLog(s"[genpc] \(what): answer is not a JSON object");
      return null;
    }
    return json as JsonObject;
  }

  private func StartTimeout(seconds: Float) -> Void {
    this.StopTimeout();
    let cb = new GenpcTimeout();
    cb.owner = this;
    this.timeoutToken = this.NewId();
    cb.token = this.timeoutToken;
    this.timeout = GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, seconds, false);
  }

  private func StopTimeout() -> Void {
    if this.timeoutToken > 0 {
      GameInstance.GetDelaySystem(this.GetGameInstance()).CancelCallback(this.timeout);
    }
    this.timeoutToken = -1;
  }

  private func StartTick() -> Void {
    let cb = new GenpcTick();
    cb.owner = this;
    cb.gen = this.tickGen;
    GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, 0.25, false);
  }
}

// Rule 23: while the panel is open, the game's own choices for the NPC are hidden.
@wrapMethod(InteractionUIBase)
protected cb func OnDialogsData(value: Variant) -> Bool {
  let player = this.GetPlayerControlledObject();
  if IsDefined(player) {
    let system = GameInstance.GetScriptableSystemsContainer(player.GetGame()).Get(n"Genpc.GenpcSystem") as GenpcSystem;
    if IsDefined(system) && system.IsPanelOpen() {
      let empty: DialogChoiceHubs;
      return wrappedMethod(ToVariant(empty));
    }
  }
  return wrappedMethod(value);
}
