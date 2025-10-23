import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import json
import os
import darkdetect

# ----------------------- DANE -----------------------
ADRESY_MIAST = {
    "Białystok": "https://bialystok.repertuary.pl",
    "Bielsko-Biała": "https://bielsko-biala.repertuary.pl",
    "Bydgoszcz": "https://bydgoszcz.repertuary.pl",
    "Bytom": "https://bytom.repertuary.pl",
    "Częstochowa": "https://czestochowa.repertuary.pl",
    "Dąbrowa Górnicza": "https://dabrowa-gornicza.repertuary.pl",
    "Gdańsk": "https://gdansk.repertuary.pl",
    "Gdynia": "https://gdynia.repertuary.pl",
    "Gliwice": "https://gliwice.repertuary.pl",
    "Jaworzno": "https://jaworzno.repertuary.pl",
    "Katowice": "https://katowice.repertuary.pl",
    "Kielce": "https://kielce.repertuary.pl",
    "Kraków": "https://krakow.repertuary.pl",
    "Lublin": "https://lublin.repertuary.pl",
    "Łódź": "https://lodz.repertuary.pl",
    "Olsztyn": "https://olsztyn.repertuary.pl",
    "Poznań": "https://poznan.repertuary.pl",
    "Radom": "https://radom.repertuary.pl",
    "Ruda Śląska": "https://ruda-slaska.repertuary.pl",
    "Rybnik": "https://rybnik.repertuary.pl",
    "Rzeszów": "https://rzeszow.repertuary.pl",
    "Sopot": "https://sopot.repertuary.pl",
    "Sosnowiec": "https://sosnowiec.repertuary.pl",
    "Szczecin": "https://szczecin.repertuary.pl",
    "Toruń": "https://torun.repertuary.pl",
    "Warszawa": "https://warszawa.repertuary.pl",
    "Wrocław": "https://wroclaw.repertuary.pl",
    "Zabrze": "https://zabrze.repertuary.pl"
}

ŚCIEŻKA_USTAWIEŃ = "ustawienia.json"
AKTUALNY_PLAN = None

# ----------------------- FUNKCJE DANYCH -----------------------
def zbuduj_adresy(miasto, dzien):
    baza = ADRESY_MIAST[miasto]
    return {
        "filmy": f"{baza}/film/actual.js",
        "kina": f"{baza}/kino/index.js",
        "repertuar": f"{baza}/cinema_program/by_hour?day={dzien}",
    }

def pobierz_dostepne_dni(miasto):
    url = f"{ADRESY_MIAST[miasto]}/cinema_program/by_hour"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        dni = []
        for opt in soup.select("select#day_select option"):
            wartosc = opt.get("value")
            tekst = opt.get_text(strip=True)
            if wartosc and tekst:
                dni.append((tekst, wartosc))
        return dni
    except Exception:
        return []

def pobierz_filmy(adres_filmow):
    resp = requests.get(adres_filmow, headers={"User-Agent": "Mozilla/5.0"})
    dane = resp.json()
    filmy = {}
    for f in dane.values():
        filmy[f["slug"]] = {
            "tytul": f["title"],
            "czas_trwania": f.get("runtime") or 120,
        }
    return filmy

def pobierz_kina(adres_kin):
    try:
        resp = requests.get(adres_kin, headers={"User-Agent": "Mozilla/5.0"})
        dane = resp.json()
        kina = [v["name"] for v in dane.values()]
        return sorted(kina)
    except Exception:
        return []

def _parsuj_godzine_na_time(godzina_txt):
    if not godzina_txt:
        return None
    godzina_txt = godzina_txt.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(godzina_txt, fmt).time()
        except ValueError:
            pass
    return None

def pobierz_seanse(filmy, adres_repertuaru, data_seansu: date, filtr_kina=None):
    resp = requests.get(adres_repertuaru, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    seanse = []

    for tabela in soup.select("table.showtimes.repert"):
        wiersze = tabela.select("tr")
        aktualna_godzina_txt = None

        for wiersz in wiersze:
            naglowek = wiersz.find("h3")
            if naglowek:
                raw = str(naglowek.contents[0]).strip() if naglowek.contents else ""
                aktualna_godzina_txt = raw
                continue

            if aktualna_godzina_txt:
                kino_tag = wiersz.select_one("td.cinema a")
                film_tag = wiersz.select_one("td a.preview-link.film")
                if not film_tag or not kino_tag:
                    continue

                kino = kino_tag.get_text(strip=True)
                tytul = film_tag.get_text(strip=True)
                slug = str(film_tag.get("href", "")).split("/")[-1].replace(".html", "")
                czas = filmy.get(slug, {}).get("czas_trwania", 120)
                if filtr_kina and kino != filtr_kina:
                    continue

                godz_time = _parsuj_godzine_na_time(aktualna_godzina_txt)
                if not godz_time:
                    continue

                start_dt = datetime.combine(data_seansu, godz_time)
                end_dt = start_dt + timedelta(minutes=czas)

                seanse.append({
                    "tytul": tytul,
                    "kino": kino,
                    "poczatek": start_dt,
                    "koniec": end_dt,
                    "czas": czas
                })
    return seanse

def uloz_maraton(seanse, przerwa_reklamowa=0, start_od=None, koniec_do=None):
    """Filtruje seanse wg czasu rozpoczęcia i zakończenia i usuwa powtarzające się tytuły."""
    if not seanse:
        return []

    data_seansu = seanse[0]["poczatek"].date()
    start_dt = datetime.combine(data_seansu, start_od) if start_od else None
    koniec_dt = datetime.combine(data_seansu, koniec_do) if koniec_do else None

    plan = []
    ostatni_koniec = None
    widziane_tytuly = set()  # aby każdy tytuł pojawił się tylko raz

    for s in sorted(seanse, key=lambda x: x["poczatek"]):
        if s["tytul"] in widziane_tytuly:
            continue  # pomiń seans jeśli tytuł już w planie

        if start_dt and s["poczatek"] < start_dt:
            continue
        if koniec_dt and s["koniec"] > koniec_dt:
            continue
        if not ostatni_koniec or s["poczatek"] >= ostatni_koniec + timedelta(minutes=przerwa_reklamowa):
            plan.append(s)
            ostatni_koniec = s["koniec"]
            widziane_tytuly.add(s["tytul"])  # zaznacz tytuł jako dodany

    return plan


# ----------------------- EKSPORT -----------------------
def eksportuj_pdf():
    if not AKTUALNY_PLAN:
        messagebox.showwarning("Brak danych", "Najpierw znajdź maraton filmowy.")
        return
    dane = AKTUALNY_PLAN
    plik = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
    if not plik:
        return
    doc = SimpleDocTemplate(plik, pagesize=A4)
    style = getSampleStyleSheet()
    story = [Paragraph(f"Maraton filmowy — {dane['miasto']}, {dane['dzien']}", style['Title'])]
    if dane["kino"]:
        story.append(Paragraph(f"Kino: {dane['kino']}", style['Normal']))
    story.append(Paragraph(f"Przerwa reklamowa: {dane['reklamy']} min", style['Normal']))
    story.append(Spacer(1, 12))
    for s in dane["plan"]:
        txt = f"{s['poczatek'].strftime('%H:%M')} - {s['koniec'].strftime('%H:%M')} | {s['tytul']} ({s['kino']}) [{s['czas']} min]"
        story.append(Paragraph(txt, style['Normal']))
    doc.build(story)
    messagebox.showinfo("Zapisano", f"PDF zapisano do:\n{plik}")

def eksportuj_csv():
    if not AKTUALNY_PLAN:
        messagebox.showwarning("Brak danych", "Najpierw znajdź maraton filmowy.")
        return
    dane = AKTUALNY_PLAN
    plik = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
    if not plik:
        return
    with open(plik, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Start", "Koniec", "Tytuł", "Kino", "Czas (min)"])
        for s in dane["plan"]:
            writer.writerow([s["poczatek"].strftime("%H:%M"), s["koniec"].strftime("%H:%M"), s["tytul"], s["kino"], s["czas"]])
    messagebox.showinfo("Zapisano", f"CSV zapisano do:\n{plik}")

def eksportuj_ics():
    if not AKTUALNY_PLAN:
        messagebox.showwarning("Brak danych", "Najpierw znajdź maraton filmowy.")
        return
    dane = AKTUALNY_PLAN
    plik = filedialog.asksaveasfilename(defaultextension=".ics", filetypes=[("iCalendar", "*.ics")])
    if not plik:
        return
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Asystent Kinomana//EN"]
    for s in dane["plan"]:
        start = s['poczatek'].strftime("%Y%m%dT%H%M%S")
        end = s['koniec'].strftime("%Y%m%dT%H%M%S")
        lines += [
            "BEGIN:VEVENT",
            f"SUMMARY:{s['tytul']}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"LOCATION:{s['kino']}",
            "END:VEVENT"
        ]
    lines.append("END:VCALENDAR")
    with open(plik, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    messagebox.showinfo("Zapisano", f"Kalendarz zapisano do:\n{plik}")

# ----------------------- MOTYW -----------------------
def ustaw_motyw_dark(style: ttk.Style):
    okno.configure(bg="#1e1e1e")
    style.theme_use("clam")
    style.configure(".", background="#1e1e1e", foreground="#ffffff", fieldbackground="#252526")
    style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
    style.configure("TButton", background="#0078d7", foreground="#ffffff", relief="flat")
    style.map("TButton", background=[("active", "#1496ff")])
    style.configure("TCombobox", fieldbackground="#252526", background="#1e1e1e", foreground="#ffffff")
    style.configure("TEntry", fieldbackground="#252526", foreground="#ffffff", insertcolor="white")
    style.configure("TLabelframe", background="#1e1e1e", foreground="#ffffff")
    style.configure("TLabelframe.Label", background="#1e1e1e", foreground="#ffffff")
    if "wynik_pole" in globals():
        wynik_pole.configure(bg="#252526", fg="#ffffff", insertbackground="white")

def ustaw_motyw_light(style: ttk.Style):
    okno.configure(bg="#f5f5f5")
    style.theme_use("clam")
    style.configure(".", background="#f5f5f5", foreground="#000000", fieldbackground="#ffffff")
    style.configure("TLabel", background="#f5f5f5", foreground="#000000")
    style.configure("TButton", background="#e0e0e0", foreground="#000000", relief="flat")
    style.map("TButton", background=[("active", "#d0d0d0")])
    style.configure("TCombobox", fieldbackground="#ffffff", background="#f5f5f5", foreground="#000000")
    style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000", insertcolor="black")
    style.configure("TLabelframe", background="#f5f5f5", foreground="#000000")
    style.configure("TLabelframe.Label", background="#f5f5f5", foreground="#000000")
    if "wynik_pole" in globals():
        wynik_pole.configure(bg="#ffffff", fg="#000000", insertbackground="black")

def przełącz_motyw():
    global aktualny_motyw
    if aktualny_motyw == "dark":
        aktualny_motyw = "light"
        ustaw_motyw_light(style)
        przycisk_motyw.config(text="🌙 Tryb ciemny")
    else:
        aktualny_motyw = "dark"
        ustaw_motyw_dark(style)
        przycisk_motyw.config(text="☀️ Tryb jasny")
    zapisz_ustawienia()

def zapisz_ustawienia():
    dane = {
        "miasto": miasto_wybrane.get(),
        "kino": kino_wybrane.get(),
        "przerwa": przerwa_reklamowa.get(),
        "godzina_od": godzina_od.get(),
        "godzina_do": godzina_do.get(),
        "dzien": pole_dnia.get(),
        "motyw": aktualny_motyw,
    }
    try:
        with open(ŚCIEŻKA_USTAWIEŃ, "w", encoding="utf-8") as f:
            json.dump(dane, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Błąd przy zapisie ustawień:", e)

def wczytaj_ustawienia():
    if not os.path.exists(ŚCIEŻKA_USTAWIEŃ):
        return
    try:
        with open(ŚCIEŻKA_USTAWIEŃ, "r", encoding="utf-8") as f:
            dane = json.load(f)
        miasto_wybrane.set(dane.get("miasto", "Wrocław"))
        kino_wybrane.set(dane.get("kino", "(Wszystkie kina)"))
        przerwa_reklamowa.set(dane.get("przerwa", "15"))
        godzina_od.set(dane.get("godzina_od", ""))
        godzina_do.set(dane.get("godzina_do", ""))
        global aktualny_motyw
        aktualny_motyw = dane.get("motyw", "dark")
        if "dzien" in dane:
            pole_dnia.set(dane["dzien"])
    except Exception as e:
        print("Błąd przy wczytywaniu ustawień:", e)

# ----------------------- MARATON -----------------------
def _parsuj_wybrana_wartosc_dnia(wybrana_str):
    if not wybrana_str:
        return date.today()
    if wybrana_str == "Dziś":
        return date.today()
    if wybrana_str == "Jutro":
        return date.today() + timedelta(days=1)
    if "(" in wybrana_str and ")" in wybrana_str:
        value = wybrana_str.split("(")[-1].strip(")")
    else:
        value = wybrana_str
    for fmt in ("%Y-%m-%d", "%m-%d"):
        try:
            if fmt == "%m-%d":
                dt = datetime.strptime(value, fmt)
                return dt.date().replace(year=date.today().year)
            else:
                return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return date.today()

def znajdz_maraton():
    global AKTUALNY_PLAN
    try:
        miasto = miasto_wybrane.get()
        wybrany_dzien_str = pole_dnia.get()
        data_seansu = _parsuj_wybrana_wartosc_dnia(wybrany_dzien_str)

        dzien_str = data_seansu.strftime("%m-%d")
        adresy = zbuduj_adresy(miasto, dzien_str)
        filmy = pobierz_filmy(adresy["filmy"])
        kino_filtr = kino_wybrane.get()
        if kino_filtr == "(Wszystkie kina)":
            kino_filtr = None

        reklamy = int(przerwa_reklamowa.get())

        start_od = None
        koniec_do = None
        if godzina_od.get():
            try:
                start_od = datetime.strptime(godzina_od.get(), "%H:%M").time()
            except ValueError:
                messagebox.showerror("Błąd", "Niepoprawny format godziny 'od' (użyj HH:MM)")
                return
        if godzina_do.get():
            try:
                koniec_do = datetime.strptime(godzina_do.get(), "%H:%M").time()
            except ValueError:
                messagebox.showerror("Błąd", "Niepoprawny format godziny 'do' (użyj HH:MM)")
                return

        seanse = pobierz_seanse(filmy, adresy["repertuar"], data_seansu, kino_filtr)
        if not seanse:
            messagebox.showwarning("Brak seansów", f"Nie znaleziono seansów w {miasto} na {dzien_str}.")
            return

        plan = uloz_maraton(seanse, reklamy, start_od, koniec_do)
        if not plan:
            messagebox.showinfo("Brak wyniku", "Nie udało się ułożyć planu.")
            return

        AKTUALNY_PLAN = {
            "plan": plan,
            "miasto": miasto,
            "kino": kino_filtr,
            "dzien": dzien_str,
            "reklamy": reklamy,
        }

        wynik_pole.delete(1.0, tk.END)
        wynik_pole.insert(tk.END, f"Maraton filmowy — {miasto}, {dzien_str}\n")
        if kino_filtr:
            wynik_pole.insert(tk.END, f"Kino: {kino_filtr}\n")
        wynik_pole.insert(tk.END, f"Przerwa reklamowa: {reklamy} min\n\n")

        for s in plan:
            wynik_pole.insert(
                tk.END,
                f"{s['poczatek'].strftime('%H:%M')} - {s['koniec'].strftime('%H:%M')} | "
                f"{s['tytul']} ({s['kino']}) [{s['czas']} min]\n"
            )

        # włącz przyciski eksportu
        przycisk_pdf.config(state="normal")
        przycisk_csv.config(state="normal")
        przycisk_ics.config(state="normal")

    except Exception as e:
        messagebox.showerror("Błąd", str(e))

# ----------------------- GUI -----------------------
okno = tk.Tk()
okno.title("Asystent Kinomana")
okno.geometry("800x720")
okno.resizable(False, False)
style = ttk.Style()
try:
    aktualny_motyw = "dark" if darkdetect.isDark() else "light"
except Exception:
    aktualny_motyw = "dark"

# ----------------------- SEKCJE -----------------------
# Ramka motywu
ramka_motyw = ttk.Frame(okno)
ramka_motyw.pack(anchor="ne", padx=10, pady=5)
przycisk_motyw = ttk.Button(ramka_motyw, text="☀️ Tryb jasny", command=przełącz_motyw)
przycisk_motyw.pack()
if aktualny_motyw == "dark":
    ustaw_motyw_dark(style)
else:
    ustaw_motyw_light(style)

# Sekcja dane
sekcja_dane = ttk.LabelFrame(okno, text="🎟️ Wybór kina i dnia", padding=10)
sekcja_dane.pack(fill="x", padx=10, pady=8)
ttk.Label(sekcja_dane, text="Miasto:").grid(row=0, column=0, sticky="w")
miasto_wybrane = tk.StringVar(value="Wrocław")
pole_miasta = ttk.Combobox(sekcja_dane, textvariable=miasto_wybrane, values=list(ADRESY_MIAST.keys()), state="readonly", width=25)
pole_miasta.grid(row=0, column=1, padx=5, pady=2)
kino_wybrane = tk.StringVar(value="(Wszystkie kina)")
ttk.Label(sekcja_dane, text="Kino:").grid(row=1, column=0, sticky="w")
pole_kina = ttk.Combobox(sekcja_dane, textvariable=kino_wybrane, state="readonly", width=25)
pole_kina.grid(row=1, column=1, padx=5, pady=2)
ttk.Label(sekcja_dane, text="Dzień repertuaru:").grid(row=2, column=0, sticky="w")
pole_dnia = ttk.Combobox(sekcja_dane, state="readonly", width=25)
pole_dnia.grid(row=2, column=1, padx=5, pady=2)

# Sekcja czas
sekcja_czas = ttk.LabelFrame(okno, text="⏰ Zakres godzin i reklamy", padding=10)
sekcja_czas.pack(fill="x", padx=10, pady=8)
godzina_od = tk.StringVar()
ttk.Label(sekcja_czas, text="Start nie wcześniej niż:").grid(row=0, column=0, sticky="w")
ttk.Entry(sekcja_czas, textvariable=godzina_od, width=10).grid(row=0, column=1, padx=5)
godzina_do = tk.StringVar()
ttk.Label(sekcja_czas, text="Koniec najpóźniej o:").grid(row=1, column=0, sticky="w")
ttk.Entry(sekcja_czas, textvariable=godzina_do, width=10).grid(row=1, column=1, padx=5)
przerwa_reklamowa = tk.StringVar(value="15")
ttk.Label(sekcja_czas, text="Przerwa reklamowa (min):").grid(row=2, column=0, sticky="w")
ttk.Combobox(sekcja_czas, textvariable=przerwa_reklamowa, values=["0","10","15","20","25","30"], state="readonly", width=8).grid(row=2, column=1, padx=5)

# Przycisk główny
ramka_przycisk = ttk.Frame(okno)
ramka_przycisk.pack(pady=10)
ttk.Button(ramka_przycisk, text="🔍 Znajdź najlepszy maraton filmowy", command=znajdz_maraton).pack(ipadx=20, ipady=5)

# Eksport
sekcja_eksport = ttk.LabelFrame(okno, text="📤 Eksport planu", padding=10)
sekcja_eksport.pack(fill="x", padx=10, pady=8)
przycisk_pdf = ttk.Button(sekcja_eksport, text="Zapisz PDF", state="disabled", command=eksportuj_pdf)
przycisk_pdf.pack(side="left", padx=5)
przycisk_csv = ttk.Button(sekcja_eksport, text="Zapisz CSV", state="disabled", command=eksportuj_csv)
przycisk_csv.pack(side="left", padx=5)
przycisk_ics = ttk.Button(sekcja_eksport, text="Zapisz do kalendarza", state="disabled", command=eksportuj_ics)
przycisk_ics.pack(side="left", padx=5)

# Wyniki
sekcja_wyniki = ttk.LabelFrame(okno, text="📋 Wyniki wyszukiwania", padding=10)
sekcja_wyniki.pack(fill="both", expand=True, padx=10, pady=10)
wynik_pole = scrolledtext.ScrolledText(sekcja_wyniki, wrap=tk.WORD, width=95, height=25, font=("Consolas", 10))
wynik_pole.pack(fill="both", expand=True)

# ----------------------- AUTOMATYCZNE ODŚWIEŻANIE -----------------------
def odswiez_kina_i_dni(*args):
    miasto = miasto_wybrane.get()
    adresy = zbuduj_adresy(miasto, date.today().strftime("%m-%d"))
    lista_kin = pobierz_kina(adresy["kina"])
    pole_kina["values"] = ["(Wszystkie kina)"] + lista_kin
    pole_kina.current(0)
    kino_wybrane.set("(Wszystkie kina)")

    dni = pobierz_dostepne_dni(miasto)
    if dni:
        wartosci = [f"{opis} ({value})" for opis, value in dni]
        pole_dnia["values"] = ["Dziś", "Jutro"] + wartosci
        pole_dnia.current(0)
    else:
        pole_dnia["values"] = ["Dziś", "Jutro"]
        pole_dnia.current(0)
    pole_dnia.set(pole_dnia["values"][0])

    if AKTUALNY_PLAN:
        znajdz_maraton()

# śledzenie zmian
miasto_wybrane.trace_add("write", odswiez_kina_i_dni)
kino_wybrane.trace_add("write", lambda *args: znajdz_maraton() if AKTUALNY_PLAN else None)
pole_dnia.bind("<<ComboboxSelected>>", lambda e: znajdz_maraton() if AKTUALNY_PLAN else None)

# ----------------------- START -----------------------
def przy_zamknieciu():
    zapisz_ustawienia()
    okno.destroy()

odswiez_kina_i_dni()
wczytaj_ustawienia()
okno.protocol("WM_DELETE_WINDOW", przy_zamknieciu)
okno.mainloop()
