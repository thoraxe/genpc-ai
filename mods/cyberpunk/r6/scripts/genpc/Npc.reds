// Facts about the NPC and the player (mod spec what/talk.md rules 7-14).
module Genpc

public abstract class GenpcNpc {
  // talk.md rule 12, 12a, 12b: the name that the game shows, "Stranger" if none, a maximum of 60 characters.
  public static func Name(npc: ref<NPCPuppet>) -> String {
    let name = npc.GetDisplayName();
    if StrBeginsWith(name, "LocKey#") {
      name = GetLocalizedText(name);
    } else {
      if GenpcNpc.IsKey(name) {
        // A crowd NPC can give a text key such as "NCResident" (PR #43 test). Show its text if the game has one.
        // Only for a key: a real name such as "Sandra Dorsett" became "Stranger" when it was looked up (2nd test).
        let text = GetLocalizedTextByKey(StringToName(name));
        if StrLen(text) > 0 && !StrBeginsWith(text, "LocKey#") {
          name = text;
        }
      }
    }
    name = StrReplaceAll(StrReplaceAll(StrReplaceAll(name, "\n", " "), "\r", " "), "\t", " ");
    if StrLen(StrReplaceAll(name, " ", "")) == 0 || StrBeginsWith(name, "LocKey#") || GenpcNpc.IsKey(name) {
      return "Stranger";
    }
    if StrLen(name) > 60 {
      return StrLeft(name, 60);
    }
    return name;
  }

  // A game text key, not a name: one word with a capital letter inside it, such as "NCResident".
  public static func IsKey(name: String) -> Bool {
    if StrContains(name, " ") || StrLen(name) < 3 {
      return false;
    }
    let i = 1;
    while i < StrLen(name) {
      let c = StrMid(name, i, 1);
      let prev = StrMid(name, i - 1, 1);
      if GenpcNpc.IsUpper(c) && (GenpcNpc.IsLower(prev) || (GenpcNpc.IsUpper(prev) && i + 1 < StrLen(name) && GenpcNpc.IsLower(StrMid(name, i + 1, 1)))) {
        return true;
      }
      i += 1;
    }
    return false;
  }

  private static func IsUpper(c: String) -> Bool {
    return NotEquals(StrUpper(c), StrLower(c)) && Equals(c, StrUpper(c));
  }

  private static func IsLower(c: String) -> Bool {
    return NotEquals(StrUpper(c), StrLower(c)) && Equals(c, StrLower(c));
  }

  public static func RecordId(npc: ref<NPCPuppet>) -> String {
    return TDBID.ToStringDEBUG(npc.GetRecordID());
  }

  public static func EntityDecimal(npc: ref<NPCPuppet>) -> String {
    return s"\(EntityID.ToHash(npc.GetEntityID()))";
  }

  // "female", "male" or "" (talk.md rule 12: only if the game gives it).
  public static func Gender(npc: ref<NPCPuppet>) -> String {
    let g = StrLower(NameToString(npc.GetGender()));
    if Equals(g, "female") || Equals(g, "male") {
      return g;
    }
    return "";
  }

  // talk.md rule 9: the starter cast, found by the name until world.md rule 7 gives the record IDs.
  public static func CastId(name: String) -> String {
    switch name {
      case "Regina Jones": return "regina_jones";
      case "Regina": return "regina_jones";
      case "Robert Wilson": return "robert_wilson";
      case "Wilson": return "robert_wilson";
      case "Cassius Ryder": return "cassius_ryder";
      case "Wakako Okada": return "wakako_okada";
      case "Wakako": return "wakako_okada";
      case "Dino Dinovic": return "dino_dinovic";
      case "Dino": return "dino_dinovic";
      case "Padre": return "padre";
      case "Sebastian Ibarra": return "padre";
      case "El Capitan": return "el_capitan";
      case "Muamar Reyes": return "el_capitan";
      case "Mr. Hands": return "mr_hands";
      case "Dakota Smith": return "dakota_smith";
      case "Dakota": return "dakota_smith";
      default: return "";
    }
  }

  // talk.md rule 11 (owner question 2): the story characters. Matched by full name or first name.
  public static func IsStoryCharacter(name: String) -> Bool {
    let names: array<String> = [
      "Jackie Welles", "Judy Alvarez", "Panam Palmer", "Johnny Silverhand", "Goro Takemura",
      "River Ward", "Kerry Eurodyne", "Viktor Vektor", "Misty Olszewski", "Evelyn Parker",
      "Dexter DeShawn", "Rogue Amendiares", "Alt Cunningham", "Saul Bright", "Mitch Anderson",
      "Lizzy Wizzy", "Hanako Arasaka"
    ];
    for full in names {
      if Equals(name, full) || Equals(name, StrBeforeFirst(full, " ")) {
        return true;
      }
    }
    // Two of them are often shown by one word only.
    return Equals(name, "Takemura") || Equals(name, "Johnny");
  }

  public static func IsDown(npc: ref<NPCPuppet>) -> Bool {
    return npc.IsDead() || ScriptedPuppet.IsUnconscious(npc) || ScriptedPuppet.IsDefeated(npc);
  }

  public static func Distance(npc: ref<NPCPuppet>, player: ref<PlayerPuppet>) -> Float {
    return Vector4.Distance(npc.GetWorldPosition(), player.GetWorldPosition());
  }

  // talk.md rules 13, 13a: the town of the district where the player is, or "" if not known.
  public static func Town(game: GameInstance) -> String {
    let prevention = GameInstance.GetScriptableSystemsContainer(game).Get(n"PreventionSystem") as PreventionSystem;
    if !IsDefined(prevention) {
      return "";
    }
    let district = prevention.GetCurrentDistrict();
    if !IsDefined(district) {
      return "";
    }
    let rec = district.GetDistrictRecord();
    let top = rec;
    while IsDefined(top) && IsDefined(top.ParentDistrictHandle()) {
      top = top.ParentDistrictHandle();
    }
    if !IsDefined(top) {
      return "";
    }
    switch top.Type() {
      case gamedataDistrict.Watson: return "watson";
      case gamedataDistrict.Westbrook: return "westbrook";
      case gamedataDistrict.CityCenter: return "city_center";
      case gamedataDistrict.Heywood: return "heywood";
      case gamedataDistrict.SantoDomingo: return "santo_domingo";
      case gamedataDistrict.Pacifica: return "pacifica";
      case gamedataDistrict.Badlands: return "badlands";
      case gamedataDistrict.NorthBadlands: return "badlands";
      case gamedataDistrict.SouthBadlands: return "badlands";
      case gamedataDistrict.MorroRock: return "badlands";
      default: return "";
    }
  }
}
