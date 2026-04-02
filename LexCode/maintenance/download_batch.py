
import os
import subprocess

amendments = [
    ("ra_2632_1960.html", "https://lawphil.net/statutes/repacts/ra1960/ra_2632_1960.html"),
    ("ra_4661_1966.html", "https://lawphil.net/statutes/repacts/ra1966/ra_4661_1966.html"),
    ("ra_6127_1970.html", "https://lawphil.net/statutes/repacts/ra1970/ra_6127_1970.html"),
    ("pd_603_1974.html", "https://lawphil.net/statutes/presdecs/pd1974/pd_603_1974.html"),
    ("pd_942_1976.html", "https://lawphil.net/statutes/presdecs/pd1976/pd_942_1976.html"),
    ("pd_1179_1977.html", "https://lawphil.net/statutes/presdecs/pd1977/pd_1179_1977.html"),
    ("pd_1239_1977.html", "https://lawphil.net/statutes/presdecs/pd1977/pd_1239_1977.html"),
    ("pd_1613_1979.html", "https://lawphil.net/statutes/presdecs/pd1979/pd_1613_1979.html"),
    ("bp_871_1985.html", "https://lawphil.net/statutes/bataspam/bp1985/bp_871_1985.html"),
    ("eo_272_1987.html", "https://lawphil.net/executive/execord/eo1987/eo_272_1987.html"),
    ("ra_6968_1990.html", "https://lawphil.net/statutes/repacts/ra1990/ra_6968_1990.html"),
    ("ra_7659_1993.html", "https://lawphil.net/statutes/repacts/ra1993/ra_7659_1993.html"),
    ("ra_8353_1997.html", "https://lawphil.net/statutes/repacts/ra1997/ra_8353_1997.html"),
    ("ra_9344_2006.html", "https://lawphil.net/statutes/repacts/ra2006/ra_9344_2006.html"),
    ("ra_10158_2012.html", "https://lawphil.net/statutes/repacts/ra2012/ra_10158_2012.html"),
    ("ra_10592_2013.html", "https://lawphil.net/statutes/repacts/ra2013/ra_10592_2013.html"),
    ("ra_10655_2015.html", "https://lawphil.net/statutes/repacts/ra2015/ra_10655_2015.html"),
    ("ra_10951_2017.html", "https://lawphil.net/statutes/repacts/ra2017/ra_10951_2017.html"),
    ("ra_11362_2019.html", "https://lawphil.net/statutes/repacts/ra2019/ra_11362_2019.html"),
    ("ra_11594_2021.html", "https://lawphil.net/statutes/repacts/ra2021/ra_11594_2021.html"),
    ("ra_11648_2022.html", "https://lawphil.net/statutes/repacts/ra2022/ra_11648_2022.html"),
    ("ra_11926_2022.html", "https://lawphil.net/statutes/repacts/ra2022/ra_11926_2022.html")
]

DEST_DIR = "data/LexCode/Codals/doc"
if not os.path.exists(DEST_DIR):
    os.makedirs(DEST_DIR)

print(f"Downloading {len(amendments)} files to {DEST_DIR}...")

for filename, url in amendments:
    filepath = os.path.join(DEST_DIR, filename)
    if os.path.exists(filepath):
        print(f"Skipping {filename} (exists)")
        continue
        
    print(f"Downloading {filename}...")
    try:
        subprocess.run(["curl", "-o", filepath, url], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {filename}: {e}")

print("Download complete.")
