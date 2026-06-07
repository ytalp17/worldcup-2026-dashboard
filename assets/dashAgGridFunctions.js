// dash-ag-grid resolves column-definition functions (e.g. comparators) from this
// namespace. Kept separate from dashAgGridComponentFunctions.js, which holds cell
// renderers (a different namespace).
var dagfuncs = (window.dashAgGridFunctions = window.dashAgGridFunctions || {});

// Convert a dd/mm/yyyy string to a comparable yyyymmdd integer.
// Blank or malformed values return null so they can be sorted to the end.
function ddmmyyyyToNumber(value) {
    if (!value) return null;
    var parts = String(value).split("/");
    if (parts.length !== 3) return null;
    var day = parseInt(parts[0], 10);
    var month = parseInt(parts[1], 10);
    var year = parseInt(parts[2], 10);
    if (isNaN(day) || isNaN(month) || isNaN(year)) return null;
    return year * 10000 + month * 100 + day;
}

// Chronological sort for dd/mm/yyyy date columns (DOB, Debut); blanks sort last.
dagfuncs.dateComparatorCustom = function (date1, date2) {
    var n1 = ddmmyyyyToNumber(date1);
    var n2 = ddmmyyyyToNumber(date2);
    if (n1 === null && n2 === null) return 0;
    if (n1 === null) return 1;
    if (n2 === null) return -1;
    return n1 - n2;
};

// Format a numeric kilometre distance in the unit chosen by the #unit-toggle
// switch (window.__journeyUnit, set by a clientside callback). Sorting still uses
// the raw numeric value, so it's correct regardless of the displayed unit.
dagfuncs.formatDistance = function (params) {
    var v = params.value;
    if (v === null || v === undefined || v === "") return "";
    if ((window.__journeyUnit || "km") === "mi") {
        return Math.round(v * 0.621371).toLocaleString() + " mi";
    }
    return Math.round(v).toLocaleString() + " km";
};

// Translucent rgba from a #rrggbb (or #rgb) hex; null if unparseable.
function hexToRgba(hex, alpha) {
    hex = String(hex || "").replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join("");
    var r = parseInt(hex.substr(0, 2), 16);
    var g = parseInt(hex.substr(2, 2), 16);
    var b = parseInt(hex.substr(4, 2), 16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return null;
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
}

// Highlight a selected team's row in that team's own flow colour (the colour
// formerly shown as the legend dot). Unselected rows get no override.
dagfuncs.journeyRowStyle = function (params) {
    if (!params.data || !params.data.selected) return null;
    var c = params.data.color || "#339af0";
    return {
        backgroundColor: hexToRgba(c, 0.32) || "rgba(51,154,240,0.28)",
        boxShadow: "inset 3px 0 0 0 " + c,
    };
};
