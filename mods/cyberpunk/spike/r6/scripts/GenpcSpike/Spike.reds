// C0 spike (issues #3, #4, #5). Throwaway code: it proves the mod stack works.
// F7: log line + on-screen text (#3), then ask the engine for the day (#4).
// F8: play sound slot 0 on the NPC you look at (#5).
module GenpcSpike

import RedHttpClient.*
import RedData.Json.*
import Audioware.*

public class SpikeSystem extends ScriptableSystem {
  private func OnAttach() -> Void {
    GameInstance.GetCallbackSystem().RegisterCallback(n"Input/Key", this, n"OnKey");
    FTLog("[genpc] spike loaded: F7 = hello + engine, F8 = sound on NPC");
  }

  private cb func OnKey(evt: ref<KeyInputEvent>) {
    if NotEquals(evt.GetAction(), EInputAction.IACT_Release) {
      return;
    }
    if Equals(evt.GetKey(), EInputKey.IK_F7) {
      FTLog("[genpc] F7 pressed");
      this.Show("genpc: hello. Asking the engine...");
      AsyncHttpClient.Get(HttpCallback.Create(this, n"OnWorld"), "http://localhost:8000/api/world");
    } else {
      if Equals(evt.GetKey(), EInputKey.IK_F8) {
        this.PlayOnNpc();
      }
    }
  }

  private cb func OnWorld(response: ref<HttpResponse>) {
    if !IsDefined(response) {
      FTLog("[genpc] engine: no reply");
      this.Show("genpc: no reply from the engine");
      return;
    }
    let code = response.GetStatusCode();
    if code != 200 {
      FTLog(s"[genpc] engine: status \(code)");
      this.Show(s"genpc: engine replied \(code)");
      return;
    }
    let json = response.GetJson();
    if !IsDefined(json) || !json.IsObject() {
      FTLog("[genpc] engine: reply is not a JSON object");
      this.Show("genpc: engine reply not readable");
      return;
    }
    let obj = json as JsonObject;
    let day = obj.GetKeyDouble("day");
    let world = obj.GetKeyString("world");
    FTLog(s"[genpc] engine: world \(world), day \(day)");
    this.Show(s"genpc: engine world \(world), day \(day)");
  }

  private func PlayOnNpc() -> Void {
    let game = this.GetGameInstance();
    let player = GetPlayer(game);
    let target = GameInstance.GetTargetingSystem(game).GetLookAtObject(player, false, false);
    if !IsDefined(target) {
      this.Show("genpc: look at an NPC first");
      return;
    }
    let id = target.GetEntityID();
    let audio = GameInstance.GetAudioSystemExt(game);
    if !audio.IsRegisteredEmitter(id, n"genpc") {
      let ok = audio.RegisterEmitter(id, n"genpc");
      FTLog(s"[genpc] RegisterEmitter: \(ok)");
    }
    audio.PlayOnEmitter(n"genpc_slot_0", id, n"genpc");
    FTLog("[genpc] F8: played genpc_slot_0");
    this.Show("genpc: playing slot 0 on this NPC");
  }

  private func Show(text: String) -> Void {
    let msg: SimpleScreenMessage;
    msg.isShown = true;
    msg.duration = 5.0;
    msg.message = text;
    let defs = GetAllBlackboardDefs().UI_Notifications;
    GameInstance.GetBlackboardSystem(this.GetGameInstance()).Get(defs).SetVariant(defs.OnscreenMessage, ToVariant(msg), true);
  }
}
