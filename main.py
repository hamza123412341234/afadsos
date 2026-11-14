python
import json
import math
import random
import string
import struct
import threading
import time
from pathlib import Path
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.utils import platform

if platform == 'android':
    from android.permissions import request_permissions, Permission
    from jnius import autoclass, PythonJavaClass, java_method

    class BleAdvertiseCallback(PythonJavaClass):
        __javainterfaces__ = ['android/bluetooth/le/AdvertiseCallback']
        __javacontext__ = 'app'

        @java_method('(Landroid/bluetooth/le/AdvertiseSettings;)V')
        def onStartSuccess(self, settingsInEffect):
            print("BLE Yayini Basariyla Basladi")

        @java_method('(I)V')
        def onStartFailure(self, errorCode):
            print(f"BLE Yayin Hatasi Kodu: {errorCode}")


class SinirliTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        kalan = 11 - len(self.text)
        if kalan > 0:
            super().insert_text(substring[:kalan], from_undo=from_undo)


class KazazedeApp(App):
    def build(self):
        self.dosya_yolu = Path(self.user_data_dir) / "profil_data.json"
        self.yayin_aktif = False
        self.siren_aktif = False
        self.advertiser = None
        self.callback = None
        self.adapter = None
        self.eski_cihaz_adi = None
        self.oturum_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
        
        self.kan_kodlari = {
            '0rh+': '1', '0rh-': '2',
            'arh+': '3', 'arh-': '4',
            'brh+': '5', 'brh-': '6',
            'abrh+': '7', 'abrh-': '8'
        }
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        if platform == 'android':
            request_permissions([
                Permission.BLUETOOTH_CONNECT,
                Permission.BLUETOOTH_ADVERTISE,
                Permission.ACCESS_FINE_LOCATION,
                Permission.POST_NOTIFICATIONS
            ])
        
        self.ad_input = SinirliTextInput(
            hint_text="Ad Soyad (Maks. 11 Karakter)", 
            multiline=False,
            size_hint_y=None, height=50
        )
        self.kan_spinner = Spinner(
            text='Kan Grubu Seciniz',
            values=('0rh+', '0rh-', 'arh+', 'arh-', 'brh+', 'brh-', 'abrh+', 'abrh-'),
            size_hint_y=None, height=50
        )
        
        self.siren_buton = Button(
            text="ACIL DUDUK / SIREN CAL", 
            background_color=(0.9, 0.5, 0.0, 1), font_size=18, bold=True
        )
        self.siren_buton.bind(on_press=self.siren_tetikle)

        self.sos_buton = Button(
            text="SOS YAYININI BASLAT", 
            background_color=(0.8, 0.1, 0.1, 1), font_size=20, bold=True
        )
        self.sos_buton.bind(on_press=self.sos_tetikle)
        
        layout.add_widget(Label(text="KAZAZEDE ACIL SINYAL PANELI", font_size=20, bold=True, size_hint_y=None, height=40))
        layout.add_widget(self.ad_input)
        layout.add_widget(self.kan_spinner)
        layout.add_widget(self.siren_buton)
        layout.add_widget(self.sos_buton)
        
        self.profil_yukle()
        return layout

    def profil_yukle(self):
        if self.dosya_yolu.exists():
            try:
                data = json.loads(self.dosya_yolu.read_text(encoding="utf-8"))
                self.ad_input.text = data.get("ad", "")[:11]
                self.kan_spinner.text = data.get("kan", "Kan Grubu Seciniz")
            except Exception:
                pass

    def veri_maskele(self, metin):
        temiz = metin.lower()
        degisim = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c"}
        for tr, en in degisim.items():
            temiz = temiz.replace(tr, en)
            
        sonuc = []
        for c in temiz:
            if c == " ":
                sonuc.append("-")
            elif c.isalnum():
                sonuc.append(chr(ord(c) + 1))
        return "".join(sonuc)

    def kalici_bildirim_yonet(self, aktif):
        if platform != 'android':
            return
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            NotificationChannel = autoclass('android.app.NotificationChannel')
            NotificationManager = autoclass('android.app.NotificationManager')
            BuildVersion = autoclass('android.os.Build$VERSION')
            PowerManager = autoclass('android.os.PowerManager')

            activity = PythonActivity.mActivity
            notif_manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            channel_id = "afad_sos_kanal"

            if aktif:
                pm = activity.getSystemService(Context.POWER_SERVICE)
                self.wake_lock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AFAD::SOSWakeLock")
                self.wake_lock.acquire()

                if BuildVersion.SDK_INT >= 26:
                    channel = NotificationChannel(channel_id, "AFAD Acil Yayin", NotificationManager.IMPORTANCE_HIGH)
                    notif_manager.createNotificationChannel(channel)
                    builder = NotificationBuilder(activity, channel_id)
                else:
                    builder = NotificationBuilder(activity)

                builder.setContentTitle("AFAD SOS YAYINI AKTIF")
                builder.setContentText("Ekran kapali olsa bile konum sinyali gonderiliyor.")
                builder.setSmallIcon(activity.getApplicationInfo().icon)
                builder.setOngoing(True)
                notif_manager.notify(1001, builder.build())
            else:
                notif_manager.cancel(1001)
                if hasattr(self, 'wake_lock') and self.wake_lock.isHeld():
                    self.wake_lock.release()
        except Exception as e:
            print("Bildirim hatasi:", e)

    def siren_tetikle(self, instance):
        if self.siren_aktif:
            self.siren_aktif = False
            self.siren_buton.text = "ACIL DUDUK / SIREN CAL"
            self.siren_buton.background_color = (0.9, 0.5, 0.0, 1)
            return

        self.siren_aktif = True
        self.siren_buton.text = "SIREN CALIYOR (DURDUR)"
        self.siren_buton.background_color = (0.1, 0.6, 0.1, 1)
        threading.Thread(target=self.yuksek_ses_uret, daemon=True).start()

    def yuksek_ses_uret(self):
        if platform == 'android':
            try:
                AudioTrack = autoclass('android.media.AudioTrack')
                AudioFormat = autoclass('android.media.AudioFormat')
                AudioManager = autoclass('android.media.AudioManager')
                AudioAttributes = autoclass('android.media.AudioAttributes')
                AudioAttributesBuilder = autoclass('android.media.AudioAttributes$Builder')
                AudioFormatBuilder = autoclass('android.media.AudioFormat$Builder')
                Context = autoclass('android.content.Context')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')

                activity = PythonActivity.mActivity
                audio_manager = activity.getSystemService(Context.AUDIO_SERVICE)
                max_vol = audio_manager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
                audio_manager.setStreamVolume(AudioManager.STREAM_ALARM, max_vol, 0)

                sample_rate = 16000
                duration = 0.5
                num_samples = int(sample_rate * duration)
                
                buffer = bytearray()
                for i in range(num_samples):
                    freq = 2600 + (1200 * abs(math.sin(math.pi * i / num_samples)))
                    sample = int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
                    buffer.extend(struct.pack('<h', sample))
                ses_verisi = bytes(buffer)

                attrs = AudioAttributesBuilder()\
                    .setUsage(AudioAttributes.USAGE_ALARM)\
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)\
                    .build()

                fmt = AudioFormatBuilder()\
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)\
                    .setSampleRate(sample_rate)\
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)\
                    .build()

                audio_track = AudioTrack(
                    attrs, fmt, len(ses_verisi),
                    AudioTrack.MODE_STREAM,
                    AudioManager.AUDIO_SESSION_ID_GENERATE
                )
                audio_track.play()

                while self.siren_aktif:
                    audio_track.write(ses_verisi, 0, len(ses_verisi))
                    time.sleep(0.05)

                audio_track.stop()
                audio_track.release()
            except Exception as e:
                print("Ses hatasi:", e)
        else:
            while self.siren_aktif:
                print("SIREN AKTIF [2600-3800 Hz]")
                time.sleep(0.5)

    def yayini_durdur_ve_temizle(self):
        if platform == 'android':
            try:
                if self.advertiser and self.callback:
                    self.advertiser.stopAdvertising(self.callback)
                if self.adapter and self.eski_cihaz_adi:
                    self.adapter.setName(self.eski_cihaz_adi)
            except Exception:
                pass
        self.kalici_bildirim_yonet(False)
        self.yayin_aktif = False

    def sos_tetikle(self, instance):
        if self.yayin_aktif:
            self.yayini_durdur_ve_temizle()
            self.sos_buton.text = "SOS YAYININI BASLAT"
            self.sos_buton.background_color = (0.8, 0.1, 0.1, 1)

return
ad_metni = self.ad_input.text.strip()
kan_metni = self.kan_spinner.text
if not ad_metni or kan_metni == 'Kan Grubu Seciniz':
self.sos_buton.text = "ALANLARI DOLDURUN!"
return
data = {"ad": ad_metni, "kan": kan_metni}
self.dosya_yolu.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
maskeli_ad = self.veri_maskele(ad_metni)
kan_kodu = self.kan_kodlari.get(kan_metni, '0')
sinyal_adi = f"SOS_{maskeli_ad}{kan_kodu}{self.oturum_id}"
if platform == 'android':
try:
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
AdvertiseSettings = autoclass('android.bluetooth.le.AdvertiseSettings')
AdvertiseData = autoclass('android.bluetooth.le.AdvertiseData')
self.adapter = BluetoothAdapter.getDefaultAdapter()
if self.adapter:
if not self.eski_cihaz_adi:
self.eski_cihaz_adi = self.adapter.getName()
self.adapter.setName(sinyal_adi)
time.sleep(0.3)
self.advertiser = self.adapter.getBluetoothLeAdvertiser()
if self.advertiser:
settings = AdvertiseSettings.Builder()
.setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
.setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
.setConnectable(False)
.build()
adv_data = AdvertiseData.Builder()
.setIncludeDeviceName(True)
.build()
self.callback = BleAdvertiseCallback()
self.advertiser.startAdvertising(settings, adv_data, self.callback)
else:
self.sos_buton.text = "CIHAZ BLE DESTEKLEMIYOR!"
return
except Exception:
self.sos_buton.text = "BLUETOOTH HATASI!"
return
self.kalici_bildirim_yonet(True)
self.yayin_aktif = True
self.sos_buton.text = "YAYIN AKTIF (DURDUR)"
self.sos_buton.background_color = (0.1, 0.6, 0.1, 1)
def on_stop(self):
self.siren_aktif = False
self.yayini_durdur_ve_temizle()
if name == 'main':
KazazedeApp().run()
