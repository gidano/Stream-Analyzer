# FFmpeg-alapú Online Stream Audio & Network Analyzer

**Nyelv / Language:** [Magyar](#magyar) | [English](#english)

---

## Magyar

### Leírás

Az alkalmazás online rádió stream esetében vizsgálja, elemzi és naplózza a kinyerhető adatok alapján az audio és hálózati üzemi paramétereket.

Az alkalmazás HU/EN kétnyelvű, és tartalmaz egy szintén kétnyelvű Súgót is, benne a mérhető paraméterek rövid leírásával.

### Előfeltételek / Telepítés

A program működéséhez FFmpeg szükséges, kétféleképpen biztosítható:

- egy telepített, Windows Path-ban elérhető FFmpeg csomag, vagy
- egy letölthető portable csomag.

Utóbbihoz a [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases) repóból az `ffmpeg-master-latest-win64-gpl-shared.zip` csomag használható.

Bontsd ki egy tetszőleges helyre, majd a csomag `\bin` mappájának tartalmát másold át abba a könyvtárba, ahol a `Stream Analyzer v1.1.exe` futtatható található (vagy fordítva: az exe-t másold a `\bin` mappába — bármelyik megoldás jó).

### Használat

1. Indítsd el a programot.
2. A Stream URL mezőbe illeszd be a vizsgálni kívánt stream címét.
3. Az Indítás gombbal kezdd meg a vizsgálatot.

### Visszajelzés

Ha hasznosnak találod, egy csillaggal a GitHub repo fejlécében jelezheted a támogatásodat. Köszönöm!

---

## English

### Description

The application examines, analyzes, and logs the audio and network operating parameters of online radio streams based on the extractable data.

The application is bilingual (HU/EN) and includes a bilingual Help section with short descriptions of the measurable parameters.

### Requirements / Installation

The program requires FFmpeg, which can be provided in one of two ways:

- an installed FFmpeg package available in the Windows PATH, or
- a downloadable portable package.

For the latter, you can use the `ffmpeg-master-latest-win64-gpl-shared.zip` package from the [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases) repository.

Extract it anywhere, then copy the contents of the package's `\bin` folder into the directory where the `Stream Analyzer v1.1.exe` executable is located (or the other way around: copy the exe into the `\bin` folder — either works).

### Usage

1. Launch the program.
2. Paste the URL of the stream you want to examine into the Stream URL field.
3. Click the Start button to begin the analysis.

### Feedback

If you find it useful, feel free to show your support with a star on the GitHub repo. Thanks!
