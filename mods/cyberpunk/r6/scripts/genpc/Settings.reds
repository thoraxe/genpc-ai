// The mod settings (mod spec what/talk.md rule 30). Needs the Mod Settings mod.
module Genpc

enum GenpcTalkKey {
  G = 0,
  H = 1,
  J = 2,
  K = 3,
  Y = 4,
  F6 = 5,
}

public class GenpcSettings {
  @runtimeProperty("ModSettings.mod", "genpc")
  @runtimeProperty("ModSettings.displayName", "Talk key")
  @runtimeProperty("ModSettings.description", "The key that opens and closes the talk panel.")
  @runtimeProperty("ModSettings.displayValues.G", "G")
  @runtimeProperty("ModSettings.displayValues.H", "H")
  @runtimeProperty("ModSettings.displayValues.J", "J")
  @runtimeProperty("ModSettings.displayValues.K", "K")
  @runtimeProperty("ModSettings.displayValues.Y", "Y")
  @runtimeProperty("ModSettings.displayValues.F6", "F6")
  public let talkKey: GenpcTalkKey = GenpcTalkKey.G;

  @runtimeProperty("ModSettings.mod", "genpc")
  @runtimeProperty("ModSettings.displayName", "Voice")
  @runtimeProperty("ModSettings.description", "Play the voice of the NPC.")
  public let voiceOn: Bool = true;

  public func Key() -> EInputKey {
    switch this.talkKey {
      case GenpcTalkKey.H: return EInputKey.IK_H;
      case GenpcTalkKey.J: return EInputKey.IK_J;
      case GenpcTalkKey.K: return EInputKey.IK_K;
      case GenpcTalkKey.Y: return EInputKey.IK_Y;
      case GenpcTalkKey.F6: return EInputKey.IK_F6;
      default: return EInputKey.IK_G;
    }
  }

  public func KeyLabel() -> String {
    switch this.talkKey {
      case GenpcTalkKey.H: return "H";
      case GenpcTalkKey.J: return "J";
      case GenpcTalkKey.K: return "K";
      case GenpcTalkKey.Y: return "Y";
      case GenpcTalkKey.F6: return "F6";
      default: return "G";
    }
  }
}
