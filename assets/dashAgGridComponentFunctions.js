// Registered automatically by dash-ag-grid. `TeamCell` renders the flag image
// (from row.data.flag) next to the team's display name (the cell value).
var dagcomponentfuncs = (window.dashAgGridComponentFunctions =
    window.dashAgGridComponentFunctions || {});

dagcomponentfuncs.TeamCell = function (props) {
    return React.createElement(
        "div",
        { className: "team-cell" },
        React.createElement("img", {
            src: props.data.flag,
            className: "team-cell__flag",
            alt: "",
        }),
        React.createElement("span", { className: "team-cell__name" }, props.value)
    );
};
