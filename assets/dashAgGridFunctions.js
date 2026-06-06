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
