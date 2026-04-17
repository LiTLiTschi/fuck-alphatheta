#Requires AutoHotkey v2.0

; ============================================================
; Rekordbox Deck Output - AHK Bridge
; Reads current left/right deck number from Rekordbox via OCR.
;
; Usage:
;   #Include rekordbox_deck_output.ahk
;   deck := GetRekordboxLeftDeck()   ; returns "1", "2", "3", "4", or "?"
;   pair := GetRekordboxDeckPair()   ; returns e.g. "1,3"
;
; Setup:
;   Run setup_deck_output.bat first to calibrate and generate
;   deck_output_config.json next to this file.
; ============================================================

global RBDeck_ScriptDir := A_ScriptDir
global RBDeck_Config    := RBDeck_ScriptDir "\deck_output_config.json"
global RBDeck_StateTxt  := RBDeck_ScriptDir "\deck_state.txt"
global RBDeck_Exe       := RBDeck_ScriptDir "\dist\RekordboxDeckOutput.exe"
global RBDeck_Py        := "python"
global RBDeck_PyScript  := RBDeck_ScriptDir "\rekordbox_deck_output.py"

; ------------------------------------------------------------------
; StartRekordboxDeckOutput()
;   Launches the background detector process.
;   Prefers compiled EXE if present, falls back to python script.
; ------------------------------------------------------------------
StartRekordboxDeckOutput() {
    global RBDeck_Config, RBDeck_StateTxt, RBDeck_Exe, RBDeck_Py, RBDeck_PyScript

    if !FileExist(RBDeck_Config)
        throw Error("deck_output_config.json missing. Run setup_deck_output.bat first.")

    if FileExist(RBDeck_Exe) {
        cmd := Format('"{}" --config "{}" --write-txt "{}" --interval 80',
            RBDeck_Exe, RBDeck_Config, RBDeck_StateTxt)
        Run(cmd, , "Hide")
        return
    }

    if !FileExist(RBDeck_PyScript)
        throw Error("rekordbox_deck_output.py not found: " RBDeck_PyScript)

    cmd := Format('"{}" "{}" --config "{}" --write-txt "{}" --interval 80',
        RBDeck_Py, RBDeck_PyScript, RBDeck_Config, RBDeck_StateTxt)
    Run(cmd, , "Hide")
}

; ------------------------------------------------------------------
; ReadRekordboxDeckState() -> Map
;   Returns Map with keys "left" and "right", values "1".."4" or "?".
; ------------------------------------------------------------------
ReadRekordboxDeckState() {
    global RBDeck_StateTxt
    state := Map("left", "?", "right", "?")

    if !FileExist(RBDeck_StateTxt)
        return state

    txt := Trim(FileRead(RBDeck_StateTxt, "UTF-8"))
    if RegExMatch(txt, "L=([1-4\?])\s+R=([1-4\?])", &m) {
        state["left"]  := m[1]
        state["right"] := m[2]
    }
    return state
}

; ------------------------------------------------------------------
; Convenience wrappers
; ------------------------------------------------------------------
GetRekordboxLeftDeck()  => ReadRekordboxDeckState()["left"]
GetRekordboxRightDeck() => ReadRekordboxDeckState()["right"]
GetRekordboxDeckPair()  {
    s := ReadRekordboxDeckState()
    return s["left"] "," s["right"]
}

; ------------------------------------------------------------------
; Auto-start detector if config is present
; ------------------------------------------------------------------
if FileExist(RBDeck_Config) {
    try StartRekordboxDeckOutput()
}

; ------------------------------------------------------------------
; Demo hotkeys - remove or adapt as needed
; ------------------------------------------------------------------

; Ctrl+Alt+D  -> show current deck state as tooltip
^!d::{
    s := ReadRekordboxDeckState()
    ToolTip "Rekordbox  Left=" s["left"] "  Right=" s["right"]
    SetTimer(() => ToolTip(), -1500)
}

; Ctrl+Alt+1  -> copy "L,R" to clipboard
^!1::{
    A_Clipboard := GetRekordboxDeckPair()
    ToolTip "Clipboard: " A_Clipboard
    SetTimer(() => ToolTip(), -1000)
}
