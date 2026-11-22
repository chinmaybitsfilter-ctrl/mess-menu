// Reads all 7 days from ssms-pilani.in and writes data/menu.json
// Usage: node scrape.mjs [url] [outfile]
import { chromium } from "playwright";
import fs from "node:fs";

const URL = process.argv[2] || "https://ssms-pilani.in/";
const OUT = process.argv[3] || "data/menu.json";
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const MONTHS = ["january","february","march","april","may","june","july","august","september","october","november","december"];

function clean(item) {
  let s = item.replace(/\s+/g, " ").trim();
  if (/[À-ÿ][\u0080-¿¤]/.test(s) || /à¤|à¥/.test(s)) s = s.replace(/\([^)]*(à¤|à¥)[^)]*\)?/g, "(ankurit)");
  s = s.replace(/\+\s*Bv\s*\(.*?\)?$/i, "+ Bournvita")
       .replace(/\bI\/C\b/g, "Ice Cream")
       .replace(/\(ltd\)/gi, "(limited)")
       .replace(/\bChapti\b/gi, "Chapati")
       .replace(/\bLasun\b/gi, "Lahsun")
       .replace(/\bGutta\b/gi, "Gatta")
       .replace(/\bStuff Kulcha\b/i, "Stuffed Kulcha")
       .replace(/\bBlack Current\b/i, "Blackcurrant")
       .replace(/\bTappore\b/i, "Tapore")
       .replace(/Green Salad \(cucumber, Beet Root, Carrot,\s*raddish\)/i, "Green Salad (cucumber, beetroot, carrot, radish)")
       .replace(/\s*\((sep veg|well cooked)\)/gi, "")
       .replace(/\(\s*limited\)/i, "(limited)")
       .replace(/(\S)\((limited)\)/i, "$1 ($2)");
  // drop long ingredient lists after dal names
  if (/^(dal|mix dal)/i.test(s)) s = s.replace(/\s*\(.*$/, "");
  // close an unbalanced bracket
  if ((s.match(/\(/g) || []).length > (s.match(/\)/g) || []).length) s += ")";
  return s.trim();
}

function parseDate(text) {
  // "23rd November 2026"
  const m = text.toLowerCase().match(/(\d{1,2})(st|nd|rd|th)?\s+([a-z]+)\s+(\d{4})/);
  if (!m) throw new Error("Bad date: " + text);
  const mon = MONTHS.indexOf(m[3]) + 1;
  if (!mon) throw new Error("Bad month: " + text);
  return `${m[4]}-${String(mon).padStart(2, "0")}-${String(m[1]).padStart(2, "0")}`;
}

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(URL, { waitUntil: "networkidle", timeout: 60000 });

const days = [];
for (const day of DAYS) {
  await page.getByRole("button", { name: `Show ${day}'s menu` }).click();
  await page.locator("main h1", { hasText: day }).first().waitFor({ timeout: 15000 });
  await page.waitForTimeout(400);
  const raw = await page.evaluate(() => {
    const main = document.querySelector("main");
    const h1 = main.querySelector("h1");
    const dateEl = h1.parentElement.querySelector("p") || h1.nextElementSibling;
    const meals = {};
    for (const ul of main.querySelectorAll("ul")) {
      // walk up until the container also holds the meal title
      let box = ul.parentElement;
      while (box && box !== main && !/(Breakfast|Lunch|Dinner)/.test(box.innerText.replace(ul.innerText, ""))) box = box.parentElement;
      if (!box || box === main) continue;
      const header = box.innerText.replace(ul.innerText, "");
      const name = header.match(/Breakfast|Lunch|Dinner/)[0];
      const time = (header.match(/\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}/) || [""])[0].replace(/\s*-\s*/, " - ");
      meals[name] = { time, items: [...ul.querySelectorAll("li")].map(li => li.innerText) };
    }
    return { title: h1.innerText.trim(), date: dateEl ? dateEl.innerText.trim() : "", meals };
  });
  if (raw.title !== day) throw new Error(`Expected ${day}, got ${raw.title}`);
  for (const m of ["Breakfast", "Lunch", "Dinner"]) {
    if (!raw.meals[m]) throw new Error(`${day}: no ${m} found`);
    raw.meals[m].items = raw.meals[m].items.map(clean).filter(i => i.length > 1);
  }
  days.push({ day, date: parseDate(raw.date), meals: { Breakfast: raw.meals.Breakfast, Lunch: raw.meals.Lunch, Dinner: raw.meals.Dinner } });
  console.log(day, parseDate(raw.date), Object.values(raw.meals).map(m => m.items.length).join("/"));
}
await browser.close();

const now = new Date(Date.now() + 5.5 * 3600e3); // IST
const fetched = `${now.getUTCDate()} ${now.toLocaleString("en-GB", { month: "short", timeZone: "UTC" })} ${now.getUTCFullYear()}`;
fs.writeFileSync(OUT, JSON.stringify({ fetched, days }, null, 1) + "\n");
console.log("wrote", OUT);
