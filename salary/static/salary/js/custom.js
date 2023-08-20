function getCookie(name) {
    let matches = document.cookie.match(new RegExp(
      "(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"
    ));
    return matches ? decodeURIComponent(matches[1]) : undefined;
}

const setCookie = (cName, cValue) => document.cookie = encodeURIComponent(cName)+"="+encodeURIComponent(cValue);
const BOOTSTRAP_ATTR_NAME = "data-bs-theme";
const THEME_RELAY_NAME = "bsThemeRelay";

let currentTheme = getCookie(THEME_RELAY_NAME);
document.documentElement.setAttribute(BOOTSTRAP_ATTR_NAME, currentTheme ? currentTheme : "dark");

function switchTheme() {
    let currentTheme = getCookie(THEME_RELAY_NAME) == "dark" ? "light" : "dark";
    setCookie(THEME_RELAY_NAME, currentTheme);
    location.reload();
}
