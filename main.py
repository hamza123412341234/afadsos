name: Build AFAD SOS APK (3 Paralel Yontem)

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  # YONTEM 1: Kivy Resmi Hazir Buildozer Konteyneri (En Hizli ve Hazir Ortam)
  yontem-1-resmi-imaj:
    runs-on: ubuntu-22.04
    container:
      image: kivy/buildozer:latest
      options: --user root
    steps:
      - name: Kodlari Cek
        uses: actions/checkout@v4

      - name: Buildozer Ayarla ve Derle
        run: |
          git config --global --add safe.directory '*'
          yes | buildozer init
          sed -i 's/requirements = python3,kivy/requirements = python3,kivy,pyjnius,android/' buildozer.spec
          sed -i 's/#android.permissions = INTERNET/android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_ADVERTISE,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WAKE_LOCK,POST_NOTIFICATIONS,MODIFY_AUDIO_SETTINGS/' buildozer.spec
          sed -i 's/#android.api = 31/android.api = 33/' buildozer.spec
          sed -i 's/#android.minapi = 21/android.minapi = 24/' buildozer.spec
          yes | buildozer -v android debug || (tail -n 80 .buildozer/android/platform/build-*/dists/*/build.log; exit 1)

      - name: APK Yukle (Yontem 1)
        uses: actions/upload-artifact@v4
        with:
          name: afad-apk-yontem1
          path: bin/*.apk

  # YONTEM 2: Klasik Kararli Python 3.10 + Kivy 2.2.1 + Cython 0.29.33
  yontem-2-klasik-kararli:
    runs-on: ubuntu-22.04
    steps:
      - name: Kodlari Cek
        uses: actions/checkout@v4

      - name: Python 3.10 Kur
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Paketleri Kur
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev automake build-essential ccache

      - name: Buildozer ve Kivy 2.2.1 Derle
        env:
          PIP_CONSTRAINT: "/tmp/constraints.txt"
        run: |
          echo "cython==0.29.33" > /tmp/constraints.txt
          echo "setuptools==69.5.1" >> /tmp/constraints.txt
          pip install -c /tmp/constraints.txt buildozer==1.5.0 cython==0.29.33 setuptools==69.5.1
          yes | buildozer init
          sed -i 's/requirements = python3,kivy/requirements = python3,kivy==2.2.1,pyjnius,android/' buildozer.spec
          sed -i 's/#android.permissions = INTERNET/android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_ADVERTISE,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WAKE_LOCK,POST_NOTIFICATIONS,MODIFY_AUDIO_SETTINGS/' buildozer.spec
          sed -i 's/#android.api = 31/android.api = 33/' buildozer.spec
          sed -i 's/#android.minapi = 21/android.minapi = 24/' buildozer.spec
          sed -i 's/#android.ndk = 25b/android.ndk = 25b/' buildozer.spec
          yes | buildozer -v android debug

      - name: APK Yukle (Yontem 2)
        uses: actions/upload-artifact@v4
        with:
          name: afad-apk-yontem2
          path: bin/*.apk

  # YONTEM 3: Modern p4a Develop + Cython Kilidi
  yontem-3-modern-develop:
    runs-on: ubuntu-22.04
    steps:
      - name: Kodlari Cek
        uses: actions/checkout@v4

      - name: Python 3.10 Kur
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Paketleri Kur
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev automake build-essential ccache

      - name: Buildozer Develop Derle
        env:
          PIP_CONSTRAINT: "/tmp/constraints.txt"
        run: |
          echo "cython==0.29.33" > /tmp/constraints.txt
          echo "setuptools==69.5.1" >> /tmp/constraints.txt
          pip install -c /tmp/constraints.txt buildozer==1.5.0 cython==0.29.33 setuptools==69.5.1
          yes | buildozer init
          sed -i 's/requirements = python3,kivy/requirements = python3,kivy==2.3.0,pyjnius,android/' buildozer.spec
          sed -i 's/#android.permissions = INTERNET/android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_ADVERTISE,BLUETOOTH_CONNECT,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WAKE_LOCK,POST_NOTIFICATIONS,MODIFY_AUDIO_SETTINGS/' buildozer.spec
          sed -i 's/#android.api = 31/android.api = 33/' buildozer.spec
          sed -i 's/#android.minapi = 21/android.minapi = 24/' buildozer.spec
          sed -i 's/#android.ndk = 25b/android.ndk = 25b/' buildozer.spec
          sed -i 's/#p4a.branch = master/p4a.branch = develop/' buildozer.spec
          yes | buildozer -v android debug

      - name: APK Yukle (Yontem 3)
        uses: actions/upload-artifact@v4
        with:
          name: afad-apk-yontem3
          path: bin/*.apk
