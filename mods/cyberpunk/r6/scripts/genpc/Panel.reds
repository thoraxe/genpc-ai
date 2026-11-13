// The talk panel, the talk hint and the text box (mod spec what/talk.md rules 5b, 15-23).
module Genpc

import Codeware.UI.*

public class GenpcPanel {
  private let root: ref<inkVerticalPanel>;
  private let name: ref<inkText>;
  private let line: ref<inkText>;
  private let choices: array<ref<inkText>>;
  private let help: ref<inkText>;
  private let hint: ref<inkText>;

  private static func Text(size: Int32, r: Float, g: Float, b: Float) -> ref<inkText> {
    let t = new inkText();
    t.SetFontFamily("base\\gameplay\\gui\\fonts\\raj\\raj.inkfontfamily");
    t.SetFontStyle(n"Regular");
    t.SetFontSize(size);
    t.SetTintColor(new HDRColor(r, g, b, 1.0));
    t.SetWrapping(true, 1100.0);
    t.SetMargin(new inkMargin(0.0, 4.0, 0.0, 4.0));
    return t;
  }

  // Make the widgets in the HUD. Call it after each load, because the game makes a new HUD.
  public func Build() -> Void {
    let window = GameInstance.GetInkSystem().GetLayer(n"inkHUDLayer").GetVirtualWindow();
    if !IsDefined(window) {
      FTLog("[genpc] no HUD layer");
      return;
    }
    this.root = new inkVerticalPanel();
    this.root.SetName(n"genpc_panel");
    this.root.SetAnchor(inkEAnchor.BottomCenter);
    this.root.SetAnchorPoint(new Vector2(0.5, 1.0));
    this.root.SetMargin(new inkMargin(0.0, 0.0, 0.0, 260.0));
    this.root.SetInteractive(false);
    this.root.SetVisible(false);
    this.root.Reparent(window);

    this.name = GenpcPanel.Text(34, 0.37, 0.96, 1.0);
    this.name.Reparent(this.root);
    this.line = GenpcPanel.Text(38, 1.0, 1.0, 1.0);
    this.line.Reparent(this.root);
    ArrayClear(this.choices);
    let i = 0;
    while i < 3 {
      let c = GenpcPanel.Text(32, 1.0, 0.85, 0.35);
      c.Reparent(this.root);
      ArrayPush(this.choices, c);
      i += 1;
    }
    this.help = GenpcPanel.Text(26, 0.7, 0.7, 0.7);
    this.help.Reparent(this.root);

    this.hint = GenpcPanel.Text(32, 1.0, 1.0, 1.0);
    this.hint.SetName(n"genpc_hint");
    this.hint.SetAnchor(inkEAnchor.Centered);
    this.hint.SetAnchorPoint(new Vector2(0.0, 0.5));
    this.hint.SetMargin(new inkMargin(120.0, 0.0, 0.0, 0.0));
    this.hint.SetInteractive(false);
    this.hint.SetVisible(false);
    this.hint.Reparent(window);
  }

  public func IsBuilt() -> Bool {
    return IsDefined(this.root);
  }

  public func ShowHint(key: String) -> Void {
    if IsDefined(this.hint) {
      this.hint.SetText(s"[\(key)] Talk");
      this.hint.SetVisible(true);
    }
  }

  public func HideHint() -> Void {
    if IsDefined(this.hint) {
      this.hint.SetVisible(false);
    }
  }

  // talk.md rule 15: the name and "…" until the line arrives.
  public func Open(npcName: String, key: String) -> Void {
    if !this.IsBuilt() {
      return;
    }
    this.name.SetText(npcName);
    this.Wait();
    this.help.SetText(s"1, 2, 3: choose    Enter: type    \(key): close");
    this.root.SetVisible(true);
  }

  public func Wait() -> Void {
    this.line.SetText("…");
    this.ClearChoices();
  }

  public func ShowLine(text: String, options: array<String>) -> Void {
    this.line.SetText(text);
    let i = 0;
    while i < 3 {
      if i < ArraySize(options) {
        this.choices[i].SetText(s"\(i + 1). \(options[i])");
      } else {
        this.choices[i].SetText("");
      }
      i += 1;
    }
  }

  // talk.md rules 28, 28b.
  public func ShowProblem(text: String) -> Void {
    this.line.SetText(text);
    this.ClearChoices();
  }

  private func ClearChoices() -> Void {
    for c in this.choices {
      c.SetText("");
    }
  }

  public func Close() -> Void {
    if IsDefined(this.root) {
      this.root.SetVisible(false);
    }
  }
}

// talk.md rule 20: the text box. The popup holds the keys, so the game's keys do nothing (rule 20a).
public class GenpcTypePopup extends InGamePopup {
  public let input: ref<HubTextInput>;
  public let owner: wref<GenpcSystem>;

  protected cb func OnCreate() {
    super.OnCreate();
    this.input = HubTextInput.Create();
    this.input.SetName(n"genpc_input");
    this.input.SetMaxLength(500);
    this.input.SetDefaultText("Say something, then press Enter");
    this.input.SetWidth(1200.0);
    this.input.Reparent(this.m_container);
  }

  protected cb func OnShown() {
    super.OnShown();
    this.GetGameController().RequestSetFocus(this.input.GetRootWidget());
    if IsDefined(this.owner) {
      this.owner.OnTypingOpened();
    }
  }

  protected cb func OnHide() {
    super.OnHide();
    if IsDefined(this.owner) {
      this.owner.OnTypingClosed();
    }
  }

  // talk.md rule 22: the game does not slow down while the player types.
  protected func SetTimeDilation() {}
  protected func ResetTimeDilation() {}
  protected func SetBackgroundBlur() {}
  protected func ResetBackgroundBlur() {}
}
