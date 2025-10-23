🍿 Asystent Kinomana
Asystent Kinomana to desktopowa aplikacja stworzona w Pythonie z użyciem tkinter, która pomaga zaplanować idealny maraton filmowy w wybranych miastach Polski. Aplikacja automatycznie pobiera repertuar kin, a następnie na podstawie kryteriów użytkownika układa optymalny harmonogram seansów, jeden po drugim.

✨ Główne funkcje
Planowanie maratonów filmowych: Automatyczne tworzenie planu seansów na podstawie wybranego miasta, kina i ram czasowych.

Pobieranie danych w czasie rzeczywistym: Aplikacja pobiera aktualne dane o filmach i repertuarze ze strony repertuary.pl.

Inteligentny algorytm: Układa seanse w logicznej kolejności, uwzględniając czas trwania filmów oraz przerwy reklamowe, a także dbając o to, by każdy film w planie pojawił się tylko raz.

Personalizacja: Możliwość filtrowania wyników według:

Miasta i konkretnego kina (lub wszystkich kin).

Dnia seansu.

Godziny rozpoczęcia i zakończenia maratonu.

Długości bloku reklamowego przed filmem.

Eksport planu: Gotowy harmonogram można łatwo wyeksportować do formatów:

PDF – do wydruku lub udostępnienia.

CSV – do dalszej analizy w arkuszu kalkulacyjnym.

iCalendar (.ics) – aby dodać seanse bezpośrednio do swojego kalendarza.

Dostosowanie interfejsu: Aplikacja posiada przełącznik między jasnym i ciemnym motywem, a także zapamiętuje ostatnio wybrane ustawienia.

📍 Wspierane miasta
Aplikacja aktualnie obsługuje następujące miasta:

Białystok

Bielsko-Biała

Bydgoszcz

Bytom

Częstochowa

Dąbrowa Górnicza

Gdańsk

Gdynia

Gliwice

Jaworzno

Katowice

Kielce

Kraków

Lublin

Łódź

Olsztyn

Poznań

Radom

Ruda Śląska

Rybnik

Rzeszów

Sopot

Sosnowiec

Szczecin

Toruń

Warszawa

Wrocław

Zabrze

🚀 Jak zacząć?
Wymagania
Python 3.x

Biblioteki wymienione w pliku requirements.txt

Instalacja
Sklonuj repozytorium:

Bash

git clone https://github.com/twoja-nazwa-uzytkownika/asystent-kinomana.git
cd asystent-kinomana
Zainstaluj wymagane biblioteki:

Bash

pip install -r requirements.txt
Plik requirements.txt powinien zawierać:

requests
beautifulsoup4
reportlab
darkdetect
Uruchom aplikację:

Bash

python twoja_nazwa_pliku.py
📖 Instrukcja obsługi
Wybierz miasto z listy rozwijanej. Aplikacja automatycznie zaktualizuje listę dostępnych kin i dni.

(Opcjonalnie) Wybierz konkretne kino, aby zawęzić wyszukiwanie. Domyślnie przeszukiwane są wszystkie kina.

Wybierz dzień, na który chcesz zaplanować maraton.

(Opcjonalnie) Określ ramy czasowe:

Start nie wcześniej niż: podaj godzinę w formacie HH:MM.

Koniec najpóźniej o: podaj godzinę w formacie HH:MM.

Ustaw przewidywany czas trwania reklam przed każdym filmem.

Kliknij przycisk "🔍 Znajdź najlepszy maraton filmowy".

Wynik pojawi się w polu poniżej. Jeśli plan zostanie znaleziony, aktywują się przyciski eksportu.

Zapisz swój plan w wybranym formacie (PDF, CSV lub .ics).

⚙️ Konfiguracja
Aplikacja automatycznie tworzy plik ustawienia.json w głównym folderze, w którym zapisywane są ostatnie wybory użytkownika, takie jak miasto, kino, długość przerwy reklamowej czy wybrany motyw. Dzięki temu nie musisz konfigurować wszystkiego od nowa przy każdym uruchomieniu.
