// Game events and the clock (mod spec what/events.md). The rule numbers below are from that file.
module Genpc

import RedHttpClient.*
import RedData.Json.*

public class GenpcEventTick extends DelayCallback {
  public let owner: wref<GenpcEvents>;
  public let gen: Int32;
  public func Call() -> Void {
    if IsDefined(this.owner) {
      this.owner.OnTick(this.gen);
    }
  }
}

public class GenpcEventTimeout extends DelayCallback {
  public let owner: wref<GenpcEvents>;
  public let token: Int32;
  public func Call() -> Void {
    if IsDefined(this.owner) {
      this.owner.OnSendTimeout(this.token);
    }
  }
}

// One NPC that the player killed or knocked out in the current fight.
public class GenpcVictim {
  public let entity: EntityID;
  public let kind: Int32;  // GenpcNpc.Kind
  public let faction: String;
  public let killed: Bool;
}

// One witness, kept as the body for POST /api/npcs, because the NPC can be gone when the event is sent.
public class GenpcWitness {
  public let entity: EntityID;
  public let distance: Float;
  public let body: ref<JsonObject>;
}

// One group of a fight event (rule 7): the same kind and faction.
public class GenpcGroup {
  public let kind: Int32;
  public let faction: String;
  public let killed: Int32;
  public let down: Int32;
}

// One event that waits to be sent.
public class GenpcOutEvent {
  public let type: String;
  public let place: String;
  public let facts: array<String>;
  public let importance: array<Int32>;
  public let witnesses: array<ref<GenpcWitness>>;
  public let ids: array<String>;
  public let next: Int32;
  public let token: Int32;
}

public class GenpcEvents extends ScriptableSystem {
  private let tickGen: Int32;
  private let playSeconds: Int32;
  private let lastTown: String;
  private let lastPlace: String;
  private let nextId: Int32;
  private let clockRefused: Bool;

  // The current fight (rules 5-9).
  private let fightOn: Bool;
  private let fightPlace: String;
  private let fightHour: Int32;
  private let lastKill: Int32;
  private let victims: array<ref<GenpcVictim>>;
  private let fightWitnesses: array<ref<GenpcWitness>>;

  // The current police chase (rules 14-16).
  private let chaseOn: Bool;
  private let chaseStars: Int32;
  private let chasePlace: String;
  private let chaseWitnesses: array<ref<GenpcWitness>>;
  private let starsListener: ref<CallbackHandle>;
  private let waitForZero: Bool;

  // Gigs (rules 10-13).
  private let journalOn: Bool;
  private let readyAt: Int32;
  private let gigsSent: array<Uint32>;

  // The events that wait to be sent, one at a time.
  private let queue: array<ref<GenpcOutEvent>>;
  private let current: ref<GenpcOutEvent>;
  private let timeout: DelayID;

  public static func Get(game: GameInstance) -> ref<GenpcEvents> {
    return GameInstance.GetScriptableSystemsContainer(game).Get(n"Genpc.GenpcEvents") as GenpcEvents;
  }

  private func OnAttach() -> Void {
    let callbacks = GameInstance.GetCallbackSystem();
    callbacks.RegisterCallback(n"Session/Ready", this, n"OnSessionReady");
    callbacks.RegisterCallback(n"Session/BeforeEnd", this, n"OnSessionEnd");
  }

  private func OnDetach() -> Void {
    let callbacks = GameInstance.GetCallbackSystem();
    callbacks.UnregisterCallback(n"Session/Ready", this);
    callbacks.UnregisterCallback(n"Session/BeforeEnd", this);
  }

  private cb func OnSessionReady(evt: ref<GameSessionEvent>) {
    // Rules 6c, 14a: a load drops the open fight, the open chase and the events of the old game.
    this.Drop("load");
    ArrayClear(this.queue);
    this.current = null;
    ArrayClear(this.gigsSent);
    this.lastTown = "";
    this.lastPlace = "";
    this.readyAt = this.playSeconds;
    this.ListenToStars();
    this.ListenToJournal();
    FTLog(s"[genpc] game hours at load: \(this.GameHours()), hour of the day \(this.Hour())");
    this.tickGen += 1;
    this.StartTick();
  }

  private cb func OnSessionEnd(evt: ref<GameSessionEvent>) {
    this.Drop("load");
    if IsDefined(this.starsListener) {
      this.WantedBar().UnregisterListenerInt(GetAllBlackboardDefs().UI_WantedBar.CurrentWantedLevel, this.starsListener);
      this.starsListener = null;
    }
    if this.journalOn {
      GameInstance.GetJournalManager(this.GetGameInstance()).UnregisterScriptCallback(this, n"OnJournalState");
      this.journalOn = false;
    }
  }

  private func Settings() -> ref<GenpcSettings> {
    let talk = GameInstance.GetScriptableSystemsContainer(this.GetGameInstance()).Get(n"Genpc.GenpcSystem") as GenpcSystem;
    return IsDefined(talk) ? talk.Settings() : null;
  }

  private func EventsOn() -> Bool {
    let settings = this.Settings();
    return !IsDefined(settings) || settings.eventsOn;
  }

  // Rules 6c, 6d, 14a: forget the open fight and the open chase. Nothing is sent for them.
  public func Drop(why: String) -> Void {
    if this.fightOn || this.chaseOn {
      FTLog(s"[genpc] event dropped: \(why)");
    }
    this.fightOn = false;
    ArrayClear(this.victims);
    ArrayClear(this.fightWitnesses);
    if this.chaseOn {
      this.waitForZero = true;  // the same chase must not start again (rule 14a)
    }
    this.chaseOn = false;
    this.chaseStars = 0;
    ArrayClear(this.chaseWitnesses);
  }

  // ---- Clock (rules 1-4, 26) ----

  private func GameHours() -> Float {
    return GameInstance.GetTimeSystem(this.GetGameInstance()).GetGameTimeStamp() / 3600.0;
  }

  public func ClockBody() -> ref<JsonObject> {
    let body = new JsonObject();
    body.SetKeyDouble("hours", Cast<Double>(this.GameHours()));
    return body;
  }

  public func SendClock(why: String) -> Void {
    this.Post("/api/clock/set", this.ClockBody(), n"OnClock", 0);
  }

  private cb func OnClock(response: ref<HttpResponse>, data: array<Variant>) {
    this.ReadClock(response);
  }

  // Rule 4: a refused clock is not an error. Rule 26: write it one time.
  public func ReadClock(response: ref<HttpResponse>) -> Void {
    if !IsDefined(response) {
      FTLog("[genpc] clock: no answer");
      return;
    }
    let code = response.GetStatusCode();
    if code == 200 {
      if this.clockRefused {
        FTLog("[genpc] clock: accepted again");
      }
      this.clockRefused = false;
      return;
    }
    if code != 400 {
      FTLog(s"[genpc] clock: error \(code)");
      return;
    }
    if !this.clockRefused {
      FTLog(s"[genpc] clock: refused, game hours \(this.GameHours()): \(response.GetText())");
    }
    this.clockRefused = true;
  }

  // ---- Tick: seconds of play (rule 6a) and the clock every 60 seconds (rule 2) ----

  private func StartTick() -> Void {
    let cb = new GenpcEventTick();
    cb.owner = this;
    cb.gen = this.tickGen;
    GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, 1.0, false);
  }

  public func OnTick(gen: Int32) -> Void {
    if gen != this.tickGen {
      return;
    }
    let ui = GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(GetAllBlackboardDefs().UI_System);
    if !ui.GetBool(GetAllBlackboardDefs().UI_System.IsInMenu) {
      this.playSeconds += 1;
      this.KeepPlace();
      if this.playSeconds % 60 == 0 {
        this.SendClock("timer");
      }
      if !this.EventsOn() {
        if this.fightOn || this.chaseOn {
          this.Drop("setting off");  // rule 6d
        }
      } else {
        this.CheckFightEnd();
      }
    }
    this.StartTick();
  }

  // Rule 5b: the last place and town that the game gave in this play.
  private func KeepPlace() -> Void {
    let game = this.GetGameInstance();
    let place = GenpcNpc.PlaceId(game);
    if StrLen(place) > 0 {
      this.lastPlace = place;
    }
    let town = GenpcNpc.Town(game);
    if StrLen(town) > 0 {
      this.lastTown = town;
    }
  }

  private func Place() -> String {
    let place = GenpcNpc.PlaceId(this.GetGameInstance());
    if StrLen(place) > 0 {
      this.lastPlace = place;
      return place;
    }
    return StrLen(this.lastPlace) > 0 ? this.lastPlace : "watson";  // rule 5b
  }

  private func Town() -> String {
    let town = GenpcNpc.Town(this.GetGameInstance());
    if StrLen(town) > 0 {
      this.lastTown = town;
      return town;
    }
    return StrLen(this.lastTown) > 0 ? this.lastTown : "watson";
  }

  private func Hour() -> Int32 {
    return GameTime.Hours(GameInstance.GetTimeSystem(this.GetGameInstance()).GetGameTime());
  }

  // Rule 7b.
  private static func TimeFact(hour: Int32) -> String {
    if hour >= 6 && hour < 12 {
      return "It happened in the morning.";
    }
    if hour >= 12 && hour < 18 {
      return "It happened in the afternoon.";
    }
    if hour >= 18 && hour < 22 {
      return "It happened in the evening.";
    }
    return "It happened at night.";
  }

  // ---- Fights (rules 5-9) ----

  public func OnNeutralized(target: EntityID, type: ENeutralizeType) -> Void {
    if !this.EventsOn() || Equals(type, ENeutralizeType.None) {
      return;
    }
    let game = this.GetGameInstance();
    let npc = GameInstance.FindEntityByID(game, target) as NPCPuppet;
    if !IsDefined(npc) || GenpcNpc.IsStoryCharacter(GenpcNpc.Name(npc)) {
      return;  // rule 9
    }
    // Unconscious is a non-lethal knock-out. Killed and Defeated (lethal damage) count as killed.
    let killed = !Equals(type, ENeutralizeType.Unconscious);
    if !this.fightOn {
      this.fightOn = true;
      this.fightPlace = this.Place();  // rule 8
      this.fightHour = this.Hour();
    }
    this.lastKill = this.playSeconds;
    let found = false;
    for v in this.victims {
      if Equals(v.entity, target) {
        found = true;
        if killed {
          v.killed = true;  // a kill after a knock-out counts as a kill
        }
      }
    }
    if !found {
      let v = new GenpcVictim();
      v.entity = target;
      v.kind = GenpcNpc.Kind(npc);
      v.faction = GenpcNpc.FactionName(npc);
      if v.kind == 0 && StrLen(v.faction) == 0 {
        v.kind = 3;  // rule 7c
      }
      if v.kind != 0 {
        v.faction = "";  // police, ordinary and unknown people are one group each (rule 7)
      }
      v.killed = killed;
      ArrayPush(this.victims, v);
      FTLog(s"[genpc] fight: \(killed ? "killed" : "knocked out") \(GenpcNpc.Name(npc)), kind \(v.kind), faction \(v.faction)");
    }
    this.fightWitnesses = GenpcEvents.WithoutWitness(this.fightWitnesses, target);  // rule 19
    this.fightWitnesses = this.FindWitnesses(this.fightWitnesses);  // rule 18
  }

  // Rule 6a: the fight ends when the player is not in combat and 60 seconds of play passed after the last kill.
  private func CheckFightEnd() -> Void {
    if !this.fightOn || this.playSeconds - this.lastKill < 60 {
      return;
    }
    let player = GetPlayer(this.GetGameInstance());
    if IsDefined(player) && player.IsInCombat() {
      return;
    }
    this.SendFight();
  }

  private func SendFight() -> Void {
    let groups: array<ref<GenpcGroup>>;
    for v in this.victims {
      let group: ref<GenpcGroup>;
      for g in groups {
        if g.kind == v.kind && Equals(g.faction, v.faction) {
          group = g;
        }
      }
      if !IsDefined(group) {
        group = new GenpcGroup();
        group.kind = v.kind;
        group.faction = v.faction;
        ArrayPush(groups, group);
      }
      if v.killed {
        group.killed += 1;
      } else {
        group.down += 1;
      }
    }
    let e = new GenpcOutEvent();
    e.type = "fight";  // rule 6b
    e.place = this.fightPlace;
    let where = GenpcNpc.PlaceName(this.fightPlace);
    for g in groups {
      let n = g.killed + g.down;
      ArrayPush(e.facts, s"A merc \(GenpcEvents.Verb(g)) \(n) \(GenpcEvents.Noun(g.kind, g.faction, n)) in \(where).");  // rules 7, 7a, 7d
      ArrayPush(e.importance, GenpcEvents.Importance(g.kind, n));
    }
    ArrayPush(e.facts, GenpcEvents.TimeFact(this.fightHour));  // rule 7b
    ArrayPush(e.importance, 1);
    e.witnesses = this.fightWitnesses;
    this.fightOn = false;
    ArrayClear(this.victims);
    this.fightWitnesses = [];
    this.Queue(e);
  }

  private static func Verb(g: ref<GenpcGroup>) -> String {
    if g.killed > 0 && g.down > 0 {
      return "killed or knocked out";
    }
    return g.killed > 0 ? "killed" : "knocked out";
  }

  private static func Noun(kind: Int32, faction: String, n: Int32) -> String {
    switch kind {
      case 0: return n == 1 ? s"\(faction) member" : s"\(faction) members";
      case 1: return n == 1 ? "NCPD officer" : "NCPD officers";
      case 2: return n == 1 ? "ordinary person" : "ordinary people";
      default: return n == 1 ? "unknown person" : "unknown people";
    }
  }

  // Rule 7 (owner question 4).
  private static func Importance(kind: Int32, n: Int32) -> Int32 {
    if kind == 1 || kind == 2 {
      return n <= 2 ? 4 : 5;
    }
    if n <= 2 {
      return 3;
    }
    return n <= 9 ? 4 : 5;
  }

  // ---- Police chases (rules 14-17) ----

  private func WantedBar() -> ref<IBlackboard> {
    return GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(GetAllBlackboardDefs().UI_WantedBar);
  }

  private func ListenToStars() -> Void {
    if !IsDefined(this.starsListener) {
      this.starsListener = this.WantedBar().RegisterListenerInt(GetAllBlackboardDefs().UI_WantedBar.CurrentWantedLevel, this, n"OnStars");
    }
  }

  protected cb func OnStars(stars: Int32) -> Bool {
    if stars == 0 {
      this.waitForZero = false;
    }
    if !this.EventsOn() || this.waitForZero {
      return true;
    }
    if stars > 0 && !this.chaseOn {
      this.chaseOn = true;
      this.chaseStars = stars;
      this.chasePlace = this.Place();  // rule 16
      ArrayClear(this.chaseWitnesses);
      this.chaseWitnesses = this.FindWitnesses(this.chaseWitnesses);  // rule 18
      return true;
    }
    if !this.chaseOn {
      return true;
    }
    if stars > this.chaseStars {
      this.chaseStars = stars;  // rule 15: the highest stars
    }
    if stars == 0 {
      this.chaseOn = false;
      if this.chaseStars >= 2 {
        this.SendChase();  // rule 14
      } else {
        ArrayClear(this.chaseWitnesses);
      }
      this.chaseStars = 0;
    }
    return true;
  }

  private func SendChase() -> Void {
    let e = new GenpcOutEvent();
    e.type = "police_chase";
    e.place = this.chasePlace;
    ArrayPush(e.facts, s"The NCPD chased a merc through \(GenpcNpc.PlaceName(this.chasePlace)).");
    ArrayPush(e.importance, this.chaseStars >= 4 ? 4 : 3);
    ArrayPush(e.facts, "The merc got away.");
    ArrayPush(e.importance, 2);
    e.witnesses = this.chaseWitnesses;
    this.chaseWitnesses = [];
    this.Queue(e);
  }

  // ---- Gigs (rules 10-13) ----

  private func ListenToJournal() -> Void {
    if !this.journalOn {
      GameInstance.GetJournalManager(this.GetGameInstance()).RegisterScriptCallback(this, n"OnJournalState", gameJournalListenerType.State);
      this.journalOn = true;
    }
  }

  protected cb func OnJournalState(hash: Uint32, className: CName, notifyOption: JournalNotifyOption, changeType: JournalChangeType) -> Bool {
    // Only a change that the game announces to the player (the "completed" message), not an old state again.
    if !Equals(className, n"gameJournalQuest") || !Equals(notifyOption, JournalNotifyOption.Notify) || !this.EventsOn() {
      return false;
    }
    // The journal can tell old states again just after a load. Those are not new.
    if this.playSeconds - this.readyAt < 10 || ArrayContains(this.gigsSent, hash) {
      return false;
    }
    let journal = GameInstance.GetJournalManager(this.GetGameInstance());
    let quest = journal.GetEntry(hash) as JournalQuest;
    if !IsDefined(quest) || !Equals(journal.GetEntryState(quest), gameJournalEntryState.Succeeded) {
      return false;  // rule 11: a failed gig sends nothing
    }
    if !GenpcEvents.IsGig(quest.GetType()) {
      return false;  // rule 11
    }
    ArrayPush(this.gigsSent, hash);
    let key = quest.GetTitle(journal);
    let title = GetLocalizedText(key);
    if StrLen(title) == 0 {
      title = key;
    }
    let e = new GenpcOutEvent();
    e.type = "gig";  // rule 10
    e.place = this.Place();  // rule 13
    ArrayPush(e.facts, s"A merc finished the gig '\(title)' in \(GenpcNpc.PlaceName(e.place)).");
    ArrayPush(e.importance, 4);
    ArrayPush(e.facts, GenpcEvents.TimeFact(this.Hour()));
    ArrayPush(e.importance, 1);
    this.Queue(e);  // rule 13a: no witnesses
    return false;
  }

  // Rule 11: gigs from fixers (Contract) and side jobs. Not: main story, NCPD scanner tasks (StreetStory,
  // CyberPsycho), vehicle offers, apartments and courier tasks.
  private static func IsGig(t: gameJournalQuestType) -> Bool {
    return Equals(t, gameJournalQuestType.Contract) || Equals(t, gameJournalQuestType.SideQuest) || Equals(t, gameJournalQuestType.MinorQuest);
  }

  // ---- Witnesses (rules 18-21b) ----

  // The list with the new witnesses added.
  private func FindWitnesses(old: array<ref<GenpcWitness>>) -> array<ref<GenpcWitness>> {
    let list = old;
    let game = this.GetGameInstance();
    let player = GetPlayer(game);
    if !IsDefined(player) {
      return list;
    }
    let query: TargetSearchQuery;
    query.testedSet = TargetingSet.Complete;
    query.searchFilter = TSF_NPC();
    query.maxDistance = 20.0;  // the witness range
    query.filterObjectByDistance = true;
    query.includeSecondaryTargets = false;
    query.ignoreInstigator = true;
    let parts: array<TS_TargetPartInfo>;
    GameInstance.GetTargetingSystem(game).GetTargetParts(player, query, parts);
    let town = this.Town();
    for part in parts {
      let component = TS_TargetPartInfo.GetComponent(part);
      let npc: ref<NPCPuppet>;
      if IsDefined(component) {
        npc = component.GetEntity() as NPCPuppet;
      }
      if IsDefined(npc) && this.CanWitness(npc, player, list) {
        let w = new GenpcWitness();
        w.entity = npc.GetEntityID();
        w.distance = GenpcNpc.Distance(npc, player);
        w.body = GenpcNpc.NpcBody(npc, GenpcNpc.Name(npc), town);
        ArrayPush(list, w);
      }
    }
    // Rule 20: keep the 5 nearest.
    while ArraySize(list) > 5 {
      let far = 0;
      let i = 1;
      while i < ArraySize(list) {
        if list[i].distance > list[far].distance {
          far = i;
        }
        i += 1;
      }
      ArrayErase(list, far);
    }
    return list;
  }

  // Rule 19, in witness range, and not two times in the list.
  private func CanWitness(npc: ref<NPCPuppet>, player: ref<PlayerPuppet>, list: array<ref<GenpcWitness>>) -> Bool {
    if this.IsVictim(npc.GetEntityID()) || GenpcEvents.HasWitness(list, npc.GetEntityID()) {
      return false;
    }
    if GenpcNpc.IsDown(npc) || npc.IsHostile() || GenpcNpc.IsStoryCharacter(GenpcNpc.Name(npc)) {
      return false;
    }
    return GenpcNpc.Distance(npc, player) <= 20.0;
  }

  private func IsVictim(entity: EntityID) -> Bool {
    for v in this.victims {
      if Equals(v.entity, entity) {
        return true;
      }
    }
    return false;
  }

  private static func HasWitness(list: array<ref<GenpcWitness>>, entity: EntityID) -> Bool {
    for w in list {
      if Equals(w.entity, entity) {
        return true;
      }
    }
    return false;
  }

  private static func WithoutWitness(list: array<ref<GenpcWitness>>, entity: EntityID) -> array<ref<GenpcWitness>> {
    let out: array<ref<GenpcWitness>>;
    for w in list {
      if !Equals(w.entity, entity) {
        ArrayPush(out, w);
      }
    }
    return out;
  }

  // ---- Sending (rules 21, 21a, 23, 25) ----

  private func Queue(e: ref<GenpcOutEvent>) -> Void {
    ArrayPush(this.queue, e);
    this.SendNext();
  }

  private func SendNext() -> Void {
    if IsDefined(this.current) || ArraySize(this.queue) == 0 {
      return;
    }
    if !this.EventsOn() {
      FTLog(s"[genpc] \(ArraySize(this.queue)) waiting events dropped: setting off");  // rule 24
      ArrayClear(this.queue);
      return;
    }
    this.current = this.queue[0];
    ArrayErase(this.queue, 0);
    this.current.token = this.NewId();
    this.current.next = 0;
    this.AddNextWitness();
  }

  // Rule 23: the engine must answer each request of the event in 10 seconds.
  private func Wait() -> Void {
    GameInstance.GetDelaySystem(this.GetGameInstance()).CancelCallback(this.timeout);
    let cb = new GenpcEventTimeout();
    cb.owner = this;
    cb.token = this.current.token;
    this.timeout = GameInstance.GetDelaySystem(this.GetGameInstance()).DelayCallback(cb, 10.0, false);  // rule 23
  }

  // Rule 21: add each witness to the engine first.
  private func AddNextWitness() -> Void {
    let e = this.current;
    this.Wait();
    if e.next < ArraySize(e.witnesses) {
      this.Post("/api/npcs", e.witnesses[e.next].body, n"OnWitness", e.token);
      return;
    }
    // Rule 2: the clock before each event.
    this.Post("/api/clock/set", this.ClockBody(), n"OnEventClock", e.token);
  }

  private cb func OnWitness(response: ref<HttpResponse>, data: array<Variant>) {
    if !this.IsCurrent(data) {
      return;
    }
    let answer = this.Answer(response);
    if IsDefined(answer) && StrLen(answer.GetKeyString("npc_id")) > 0 {
      let id = answer.GetKeyString("npc_id");
      if !ArrayContains(this.current.ids, id) {
        ArrayPush(this.current.ids, id);  // two NPCs of one record are one engine NPC
      }
    } else {
      FTLog(s"[genpc] event: a witness was refused (\(GenpcEvents.Code(response))), left out");  // rule 21a
    }
    this.current.next += 1;
    this.AddNextWitness();
  }

  private cb func OnEventClock(response: ref<HttpResponse>, data: array<Variant>) {
    if !this.IsCurrent(data) {
      return;
    }
    this.ReadClock(response);
    let e = this.current;
    if ArraySize(e.ids) > 0 && !Equals(e.type, "gig") {
      ArrayPush(e.facts, "The merc was the person who is talking to you now.");  // rule 21b
      ArrayPush(e.importance, 1);
    }
    let body = new JsonObject();
    body.SetKeyString("type", e.type);
    body.SetKeyString("location", e.place);
    let facts = new JsonArray();
    let i = 0;
    while i < ArraySize(e.facts) {
      let fact = new JsonObject();
      fact.SetKeyString("text", e.facts[i]);
      fact.SetKeyInt64("importance", Cast<Int64>(e.importance[i]));
      facts.AddItem(fact);
      i += 1;
    }
    body.SetKey("facts", facts);
    let witnesses = new JsonArray();
    for id in e.ids {
      witnesses.AddItemString(id);
    }
    body.SetKey("witnesses", witnesses);
    this.Wait();
    this.Post("/api/events", body, n"OnEventSent", e.token);
  }

  private cb func OnEventSent(response: ref<HttpResponse>, data: array<Variant>) {
    if !this.IsCurrent(data) {
      return;
    }
    let e = this.current;
    // Rule 25.
    FTLog(s"[genpc] event \(e.type) at \(e.place), \(ArraySize(e.ids)) witnesses: \(GenpcEvents.Code(response))");
    for fact in e.facts {
      FTLog(s"[genpc]   \(fact)");
    }
    if !IsDefined(this.Answer(response)) {
      FTLog("[genpc] event lost");  // rule 23
    }
    this.Finish();
  }

  public func OnSendTimeout(token: Int32) -> Void {
    if !IsDefined(this.current) || this.current.token != token {
      return;
    }
    FTLog(s"[genpc] event \(this.current.type) lost: no answer in 10 seconds (step \(this.current.next))");  // rule 23
    this.Finish();
  }

  private func Finish() -> Void {
    GameInstance.GetDelaySystem(this.GetGameInstance()).CancelCallback(this.timeout);
    this.current = null;
    this.SendNext();
  }

  // ---- HTTP helpers ----

  private func NewId() -> Int32 {
    this.nextId += 1;
    return this.nextId;
  }

  private func IsCurrent(data: array<Variant>) -> Bool {
    return IsDefined(this.current) && ArraySize(data) > 0 && FromVariant<Int32>(data[0]) == this.current.token;
  }

  private func Post(path: String, body: ref<JsonVariant>, callback: CName, id: Int32) -> Void {
    AsyncHttpClient.PostJson(HttpCallback.Create(this, callback, [ToVariant(id)]), "http://localhost:8000" + path, body);
  }

  private static func Code(response: ref<HttpResponse>) -> String {
    return IsDefined(response) ? s"\(response.GetStatusCode())" : "no answer";
  }

  private func Answer(response: ref<HttpResponse>) -> ref<JsonObject> {
    if !IsDefined(response) || response.GetStatusCode() != 200 {
      return null;
    }
    let json = response.GetJson();
    if !IsDefined(json) || !json.IsObject() {
      return null;
    }
    return json as JsonObject;
  }
}

// Rules 5, 6: the game names the player as the killer (also with a car, a quickhack or a grenade).
@wrapMethod(PlayerPuppet)
protected cb func OnTargetNeutraliziedEvent(evt: ref<TargetNeutraliziedEvent>) -> Bool {
  let events = GenpcEvents.Get(this.GetGame());
  if IsDefined(events) {
    events.OnNeutralized(evt.targetID, evt.type);
  }
  return wrappedMethod(evt);
}

// Rules 6c, 14a: the player died. The open fight and chase are dropped.
@wrapMethod(PlayerPuppet)
protected cb func OnDeath(evt: ref<gameDeathEvent>) -> Bool {
  let events = GenpcEvents.Get(this.GetGame());
  if IsDefined(events) {
    events.Drop("player died");
  }
  return wrappedMethod(evt);
}
