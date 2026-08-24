// 괄호를 문자스타일로.jsx
// (…) 안의 글자에 고른 문자 스타일을 입히고 괄호는 지운다.
// 반각 ( ) 와 전각 （ ） 둘 다 처리한다.

#target indesign

(function () {

    if (app.documents.length === 0) {
        alert("문서를 먼저 여세요.");
        return;
    }
    var doc = app.activeDocument;

    // ---- 문서에 있는 문자 스타일 이름 모으기 ----
    var all = doc.allCharacterStyles;
    var names = [];
    var styles = [];
    for (var i = 0; i < all.length; i++) {
        var n = all[i].name;
        if (n === "[None]" || n === "[없음]") continue;
        names.push(n);
        styles.push(all[i]);
    }
    if (names.length === 0) {
        alert("문서에 문자 스타일이 없습니다.\n먼저 윗첨자용 문자 스타일을 만들어 주세요.");
        return;
    }

    // 지난번에 고른 스타일을 기억해 둔다
    var remembered = 0;
    try {
        var last = app.extractLabel("괄호문자스타일_최근");
        for (var k = 0; k < names.length; k++) {
            if (names[k] === last) { remembered = k; break; }
        }
    } catch (e) {}

    // ---- 대화상자 ----
    var hasSel = false;
    try {
        hasSel = (app.selection.length > 0 &&
                  app.selection[0].hasOwnProperty("changeGrep"));
    } catch (e) {}

    var dlg = app.dialogs.add({ name: "괄호를 문자스타일로" });
    var dd, cbSel, cbKeep;
    var col = dlg.dialogColumns.add();

    var r1 = col.dialogRows.add();
    r1.staticTexts.add({ staticLabel: "문자 스타일:" });
    dd = r1.dropdowns.add({ stringList: names, selectedIndex: remembered });

    var r2 = col.dialogRows.add();
    cbSel = r2.checkboxControls.add({
        staticLabel: "선택한 글자에만 (끄면 문서 전체)",
        checkedState: hasSel
    });

    var r3 = col.dialogRows.add();
    cbKeep = r3.checkboxControls.add({
        staticLabel: "괄호를 남겨둔다 (서식만 입힘)",
        checkedState: false
    });

    if (!dlg.show()) { dlg.destroy(); return; }

    var chosen = styles[dd.selectedIndex];
    var chosenName = names[dd.selectedIndex];
    var onlySel = cbSel.checkedState;
    var keepParens = cbKeep.checkedState;
    dlg.destroy();

    try { app.insertLabel("괄호문자스타일_최근", chosenName); } catch (e) {}

    // ---- 대상 정하기 ----
    var target = doc;
    if (onlySel) {
        if (!hasSel) {
            alert("선택한 글자가 없습니다. 문자 도구로 글을 선택하거나\n체크를 끄고 다시 실행하세요.");
            return;
        }
        target = app.selection[0];
    }

    // ---- GREP 바꾸기 ----
    app.findGrepPreferences = NothingEnum.NOTHING;
    app.changeGrepPreferences = NothingEnum.NOTHING;
    var prevFootnotes = app.findChangeGrepOptions.includeFootnotes;
    var prevHidden = app.findChangeGrepOptions.includeHiddenLayers;
    app.findChangeGrepOptions.includeFootnotes = true;
    app.findChangeGrepOptions.includeHiddenLayers = false;

    app.findGrepPreferences.findWhat = "[(（]([^()（）]+)[)）]";
    app.changeGrepPreferences.changeTo = keepParens ? "$0" : "$1";
    app.changeGrepPreferences.appliedCharacterStyle = chosen;

    var count = 0;
    var err = null;
    try {
        count = target.changeGrep().length;
    } catch (e) {
        err = e;
    }

    app.findGrepPreferences = NothingEnum.NOTHING;
    app.changeGrepPreferences = NothingEnum.NOTHING;
    app.findChangeGrepOptions.includeFootnotes = prevFootnotes;
    app.findChangeGrepOptions.includeHiddenLayers = prevHidden;

    if (err) {
        alert("바꾸는 중에 문제가 생겼습니다:\n" + err);
        return;
    }

    alert(count + "곳에 '" + chosenName + "' 을(를) 입혔습니다." +
          (keepParens ? "\n(괄호는 남겨뒀습니다)" : "\n(괄호는 지웠습니다)"));

})();
