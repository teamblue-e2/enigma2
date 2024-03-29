from config import config, ConfigSubsection, ConfigSlider, ConfigYesNo, ConfigNothing, ConfigSelection
from enigma import eDBoxLCD
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from Screens.InfoBar import InfoBar
from Screens.Screen import Screen

from boxbranding import getBoxType


class dummyScreen(Screen):
	skin = """<screen position="0,0" size="0,0" transparent="1">
	<widget source="session.VideoPicture" render="Pig" position="0,0" size="0,0" backgroundColor="transparent" zPosition="1"/>
	</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.close()


class LCD:
	def __init__(self):
		pass

	def setBright(self, value):
		value *= 255
		value /= 10
		if value > 255:
			value = 255
		eDBoxLCD.getInstance().setLCDBrightness(value)

	def setContrast(self, value):
		value *= 63
		value //= 20
		if value > 63:
			value = 63
		eDBoxLCD.getInstance().setLCDContrast(value)

	def setInverted(self, value):
		if value:
			value = 255
		eDBoxLCD.getInstance().setInverted(value)

	def setFlipped(self, value):
		eDBoxLCD.getInstance().setFlipped(value)

	def setScreenShot(self, value):
		eDBoxLCD.getInstance().setDump(value)

	def isOled(self):
		return eDBoxLCD.getInstance().isOled()


def leaveStandby():
	config.lcd.bright.apply()


def standbyCounterChanged(dummy):
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)
	config.lcd.standby.apply()


def InitLcd():
	if getBoxType() in ('gb800se', 'gb800solo', 'gb800seplus', 'gbipbox', 'gbultra', 'gbultrase', 'spycat', 'quadbox2400', 'gbx1', 'gbx2', 'gbx3', 'gbx3h', 'gbx34k'):
		detected = False
	else:
		detected = eDBoxLCD.getInstance() and eDBoxLCD.getInstance().detected()

	SystemInfo["Display"] = detected
	config.lcd = ConfigSubsection()

	if fileExists("/proc/stb/lcd/mode"):
		f = open("/proc/stb/lcd/mode", "r")
		can_lcdmodechecking = f.read().strip().split(" ")
		f.close()
	else:
		can_lcdmodechecking = False

	SystemInfo["LCDMiniTV"] = can_lcdmodechecking

	if detected:
		ilcd = LCD()
		if can_lcdmodechecking:
			def setLCDModeMinitTV(configElement):
				try:
					f = open("/proc/stb/lcd/mode", "w")
					f.write(configElement.value)
					f.close()
				except:
					pass

			def setMiniTVFPS(configElement):
				try:
					f = open("/proc/stb/lcd/fps", "w")
					f.write("%d \n" % configElement.value)
					f.close()
				except:
					pass

			def setLCDModePiP(configElement):
				pass

			def setLCDScreenshot(configElement):
				ilcd.setScreenShot(configElement.value)

			config.lcd.modepip = ConfigSelection(default="0", choices=[
					("0", _("off")),
					("5", _("PIP")),
					("7", _("PIP with OSD"))])

			if getBoxType() in ('gbquad', 'gbquadplus'):
				config.lcd.modepip.addNotifier(setLCDModePiP)
			else:
				config.lcd.modepip = ConfigNothing()

			config.lcd.screenshot = ConfigYesNo(default=False)
			config.lcd.screenshot.addNotifier(setLCDScreenshot)

			config.lcd.modeminitv = ConfigSelection(default="0", choices=[
					("0", _("normal")),
					("1", _("MiniTV - video0")),
					("2", _("OSD - fb")),
					("3", _("MiniTV with OSD - video0+fb"))])
			config.lcd.fpsminitv = ConfigSlider(default=30, limits=(0, 30))
			config.lcd.modeminitv.addNotifier(setLCDModeMinitTV)
			config.lcd.fpsminitv.addNotifier(setMiniTVFPS)
		else:
			config.lcd.modeminitv = ConfigNothing()
			config.lcd.modepip = ConfigNothing()
			config.lcd.screenshot = ConfigNothing()
			config.lcd.fpsminitv = ConfigNothing()

		def setLCDbright(configElement):
			ilcd.setBright(configElement.value)

		def setLCDcontrast(configElement):
			ilcd.setContrast(configElement.value)

		def setLCDinverted(configElement):
			ilcd.setInverted(configElement.value)

		def setLCDflipped(configElement):
			ilcd.setFlipped(configElement.value)

		standby_default = 0

		if not ilcd.isOled():
			config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
			config.lcd.contrast.addNotifier(setLCDcontrast)
		else:
			config.lcd.contrast = ConfigNothing()
			standby_default = 1

		config.lcd.standby = ConfigSlider(default=standby_default, limits=(0, 10))
		config.lcd.standby.addNotifier(setLCDbright)
		config.lcd.standby.apply = lambda: setLCDbright(config.lcd.standby)
		config.lcd.bright = ConfigSlider(default=5, limits=(0, 10))
		config.lcd.bright.addNotifier(setLCDbright)
		config.lcd.bright.apply = lambda: setLCDbright(config.lcd.bright)
		config.lcd.bright.callNotifiersOnSaveAndCancel = True
		config.lcd.invert = ConfigYesNo(default=False)
		config.lcd.invert.addNotifier(setLCDinverted)
		config.lcd.flip = ConfigYesNo(default=False)
		config.lcd.flip.addNotifier(setLCDflipped)

		if SystemInfo["LedPowerColor"]:
			def setLedPowerColor(configElement):
				open(SystemInfo["LedPowerColor"], "w").write(configElement.value)
			config.lcd.ledpowercolor = ConfigSelection(default="1", choices=[("0", _("off")), ("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
			config.lcd.ledpowercolor.addNotifier(setLedPowerColor)

		if SystemInfo["LedStandbyColor"]:
			def setLedStandbyColor(configElement):
				open(SystemInfo["LedStandbyColor"], "w").write(configElement.value)
			config.lcd.ledstandbycolor = ConfigSelection(default="3", choices=[("0", _("off")), ("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
			config.lcd.ledstandbycolor.addNotifier(setLedStandbyColor)

		if SystemInfo["LedSuspendColor"]:
			def setLedSuspendColor(configElement):
				open(SystemInfo["LedSuspendColor"], "w").write(configElement.value)
			config.lcd.ledsuspendcolor = ConfigSelection(default="2", choices=[("0", _("off")), ("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
			config.lcd.ledsuspendcolor.addNotifier(setLedSuspendColor)

		if SystemInfo["Power4x7On"]:
			def setPower4x7On(configElement):
				open(SystemInfo["Power4x7On"], "w").write(configElement.value)
			config.lcd.power4x7on = ConfigSelection(default="on", choices=[("off", _("Off")), ("on", _("On"))])
			config.lcd.power4x7on.addNotifier(setPower4x7On)

		if SystemInfo["Power4x7Standby"]:
			def setPower4x7Standby(configElement):
				open(SystemInfo["Power4x7Standby"], "w").write(configElement.value)
			config.lcd.power4x7standby = ConfigSelection(default="on", choices=[("off", _("Off")), ("on", _("On"))])
			config.lcd.power4x7standby.addNotifier(setPower4x7Standby)

		if SystemInfo["Power4x7Suspend"]:
			def setPower4x7Suspend(configElement):
				open(SystemInfo["Power4x7Suspend"], "w").write(configElement.value)
			config.lcd.power4x7suspend = ConfigSelection(default="off", choices=[("off", _("Off")), ("on", _("On"))])
			config.lcd.power4x7suspend.addNotifier(setPower4x7Suspend)

		if SystemInfo["LcdLiveTV"]:
			def lcdLiveTvChanged(configElement):
				setLCDLiveTv(configElement.value)
				configElement.save()
			config.lcd.showTv = ConfigYesNo(default=False)
			config.lcd.showTv.addNotifier(lcdLiveTvChanged)

			if "live_enable" in SystemInfo["LcdLiveTV"]:
				config.misc.standbyCounter.addNotifier(standbyCounterChangedLCDLiveTV, initial_call=False)
	else:
		def doNothing():
			pass
		config.lcd.contrast = ConfigNothing()
		config.lcd.bright = ConfigNothing()
		config.lcd.standby = ConfigNothing()
		config.lcd.bright.apply = lambda: doNothing()
		config.lcd.standby.apply = lambda: doNothing()

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call=False)


def setLCDLiveTv(value):
	if "live_enable" in SystemInfo["LcdLiveTV"]:
		open(SystemInfo["LcdLiveTV"], "w").write(value and "enable" or "disable")
	else:
		open(SystemInfo["LcdLiveTV"], "w").write(value and "0" or "1")
	if not value:
		try:
			InfoBarInstance = InfoBar.instance
			InfoBarInstance and InfoBarInstance.session.open(dummyScreen)
		except:
			pass


def leaveStandbyLCDLiveTV():
	if config.lcd.showTv.value:
		setLCDLiveTv(True)


def standbyCounterChangedLCDLiveTV(dummy):
	if config.lcd.showTv.value:
		from Screens.Standby import inStandby
		if leaveStandbyLCDLiveTV not in inStandby.onClose:
			inStandby.onClose.append(leaveStandbyLCDLiveTV)
		setLCDLiveTv(False)
