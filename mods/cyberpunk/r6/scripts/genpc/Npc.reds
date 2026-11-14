// Facts about the NPC and the player (mod spec what/talk.md rules 7-14).
module Genpc

import RedData.Json.*

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

  // The body of POST /api/npcs (talk.md rules 9-14). Also for a witness (events.md rule 21).
  public static func NpcBody(npc: ref<NPCPuppet>, name: String, town: String) -> ref<JsonObject> {
    let body = new JsonObject();
    let cast = GenpcNpc.CastId(name);
    let record = GenpcNpc.RecordId(npc);
    if StrLen(cast) > 0 {
      body.SetKeyString("record_id", cast);
    } else {
      if npc.IsCrowd() || StrLen(record) == 0 {
        body.SetKeyString("entity_id", GenpcNpc.EntityDecimal(npc));
      } else {
        body.SetKeyString("record_id", record);
      }
    }
    body.SetKeyString("name", name);
    body.SetKeyString("settlement", town);
    let gender = GenpcNpc.Gender(npc);
    if StrLen(gender) > 0 {
      body.SetKeyString("gender", gender);
    }
    return body;
  }

  // events.md rules 5-5c: the place id of the part of the district where the player is, else of the
  // district, or "dogtown" (not in the world file), or "" if the game gives no district.
  public static func PlaceId(game: GameInstance) -> String {
    let rec = GenpcNpc.DistrictRecord(game);
    let up = rec;
    while IsDefined(up) {
      if Equals(up.Type(), gamedataDistrict.Dogtown) {
        return "dogtown";
      }
      up = up.ParentDistrictHandle();
    }
    // Walk up from the smallest area (for example LittleChina_Afterlife) to the first one in the world file.
    let r = rec;
    while IsDefined(r) {
      let id = GenpcNpc.PartId(r.Type());
      if StrLen(id) > 0 {
        return id;
      }
      r = r.ParentDistrictHandle();
    }
    return "";
  }

  private static func DistrictRecord(game: GameInstance) -> ref<District_Record> {
    let prevention = GameInstance.GetScriptableSystemsContainer(game).Get(n"PreventionSystem") as PreventionSystem;
    if !IsDefined(prevention) {
      return null;
    }
    let district = prevention.GetCurrentDistrict();
    if !IsDefined(district) {
      return null;
    }
    return district.GetDistrictRecord();
  }

  // The parts of the districts and the districts in the world file (world.md). Each area of the Badlands is "badlands".
  private static func PartId(t: gamedataDistrict) -> String {
    switch t {
      case gamedataDistrict.LittleChina: return "little_china";
      case gamedataDistrict.Kabuki: return "kabuki";
      case gamedataDistrict.Northside: return "northside";
      case gamedataDistrict.ArasakaWaterfront: return "arasaka_waterfront";
      case gamedataDistrict.JapanTown: return "japantown";
      case gamedataDistrict.CharterHill: return "charter_hill";
      case gamedataDistrict.NorthOaks: return "north_oak";
      case gamedataDistrict.CorpoPlaza: return "corpo_plaza";
      case gamedataDistrict.Downtown: return "downtown";
      case gamedataDistrict.Glen: return "the_glen";
      case gamedataDistrict.Wellsprings: return "wellsprings";
      case gamedataDistrict.VistaDelRey: return "vista_del_rey";
      case gamedataDistrict.Arroyo: return "arroyo";
      case gamedataDistrict.RanchoCoronado: return "rancho_coronado";
      case gamedataDistrict.Coastview: return "coastview";
      case gamedataDistrict.WestWindEstate: return "west_wind_estate";
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

  // The name of a place id in a fact. Example: "A merc killed 4 Maelstrom members in Northside."
  public static func PlaceName(id: String) -> String {
    switch id {
      case "little_china": return "Little China";
      case "kabuki": return "Kabuki";
      case "northside": return "Northside";
      case "arasaka_waterfront": return "Arasaka Waterfront";
      case "japantown": return "Japantown";
      case "charter_hill": return "Charter Hill";
      case "north_oak": return "North Oak";
      case "corpo_plaza": return "Corpo Plaza";
      case "downtown": return "Downtown";
      case "the_glen": return "The Glen";
      case "wellsprings": return "Wellsprings";
      case "vista_del_rey": return "Vista del Rey";
      case "arroyo": return "Arroyo";
      case "rancho_coronado": return "Rancho Coronado";
      case "coastview": return "Coastview";
      case "west_wind_estate": return "West Wind Estate";
      case "watson": return "Watson";
      case "westbrook": return "Westbrook";
      case "city_center": return "City Center";
      case "heywood": return "Heywood";
      case "santo_domingo": return "Santo Domingo";
      case "pacifica": return "Pacifica";
      case "badlands": return "the Badlands";
      case "dogtown": return "Dogtown";
      default: return id;
    }
  }

  // events.md rule 7: the kind of a killed NPC. 0 = a faction, 1 = police, 2 = ordinary people, 3 = not known.
  public static func Kind(npc: ref<NPCPuppet>) -> Int32 {
    let t = GenpcNpc.Affiliation(npc);
    if npc.IsCharacterPolice() || Equals(t, gamedataAffiliation.NCPD) {
      return 1;
    }
    if GenpcNpc.IsFaction(t) {
      return 0;
    }
    if npc.IsCharacterCivilian() || npc.IsCrowd() || Equals(t, gamedataAffiliation.Civilian) || Equals(t, gamedataAffiliation.Unaffiliated) {
      return 2;
    }
    return 3;
  }

  // The faction name in a fact. Example: "Maelstrom".
  public static func FactionName(npc: ref<NPCPuppet>) -> String {
    let rec = TweakDBInterface.GetCharacterRecord(npc.GetRecordID());
    if !IsDefined(rec) || !IsDefined(rec.Affiliation()) {
      return "";
    }
    let aff = rec.Affiliation();
    let text = GetLocalizedTextByKey(aff.LocalizedName());
    if StrLen(text) == 0 || StrBeginsWith(text, "LocKey#") {
      text = NameToString(aff.EnumName());
    }
    return text;
  }

  private static func Affiliation(npc: ref<NPCPuppet>) -> gamedataAffiliation {
    let rec = TweakDBInterface.GetCharacterRecord(npc.GetRecordID());
    if !IsDefined(rec) || !IsDefined(rec.Affiliation()) {
      return gamedataAffiliation.Invalid;
    }
    return rec.Affiliation().Type();
  }

  private static func IsFaction(t: gamedataAffiliation) -> Bool {
    switch t {
      case gamedataAffiliation.Civilian: return false;
      case gamedataAffiliation.Unaffiliated: return false;
      case gamedataAffiliation.UnaffiliatedCorpo: return false;
      case gamedataAffiliation.Unknown: return false;
      case gamedataAffiliation.Invalid: return false;
      case gamedataAffiliation.Count: return false;
      case gamedataAffiliation.NCPD: return false;
      default: return true;
    }
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
