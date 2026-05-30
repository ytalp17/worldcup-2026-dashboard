// Functions-as-props registry for dash-mantine-components (Mantine 8).
// MiniCalendar.getDayProps={"function": "wcMatchDay"} calls this per day.
var dmcfuncs = (window.dashMantineFunctions = window.dashMantineFunctions || {});

// Mark days that have a World Cup match scheduled so they blink (CSS handles
// the pulse). The match-day list is injected as window.WC_MATCH_DATES by the
// app's index template (sourced from the Python MatchCalendar).
dmcfuncs.wcMatchDay = function (day) {
  var set = window.WC_MATCH_DATES || [];
  var d = day instanceof Date ? day : new Date(day);
  // Build a local YYYY-MM-DD key (avoid UTC methods, which can shift the day).
  var pad = function (n) {
    return (n < 10 ? "0" : "") + n;
  };
  var key = d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  if (set.indexOf(key) !== -1) {
    return { className: "calendar-match-day" };
  }
  return {};
};
