from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import config
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Harddisk import harddiskmanager, getProcMounts
from Components.NimManager import nimmanager
from Components.About import about
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.config import config
from enigma import eGetEnigmaDebugLvl, getE2Rev

from Components.Pixmap import MultiPixmap
from Components.Network import iNetwork
from Components.SystemInfo import BoxInfo

from Components.Label import Label
from Components.ProgressBar import ProgressBar
from os import popen
from Tools.StbHardware import getFPVersion

from boxbranding import getBoxType, getMachineBuild, getImageVersion, getImageType
boxtype = getBoxType()

from enigma import eTimer, eLabel, eConsoleAppContainer, getDesktop
import six

from Components.GUIComponent import GUIComponent
from skin import applySkinFactor, parameters, parseScale

import os
import glob


class About(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		hddsplit = parameters.get("AboutHddSplit", 0)

		BoxName = "%s %s" % (BoxInfo.getItem("displaybrand"), BoxInfo.getItem("displaymodel"))
		self.setTitle(_("About") + " " + BoxName)
		ImageType = BoxInfo.getItem("imagetype")
		self["ImageType"] = StaticText(ImageType)

		Boxserial = popen('cat /proc/stb/info/sn').read().strip()
		serial = ""
		if Boxserial != "":
			serial = Boxserial
		cpu = about.getCPUInfoString()

		AboutText = _("Hardware: ") + BoxName + "\n"
		AboutText += _("Serial: ") + serial + "\n"
		AboutText += _("CPU: ") + cpu + "\n"
		AboutText += _("Image: ") + about.getImageTypeString() + " " + ImageType + "\n"
		AboutText += _("Image revision: ") + getE2Rev() +  "\n"
		AboutText += _("OE Version: ") + about.getOEVersionString() + "\n"
		ImageVersion = _("Last upgrade: ") + about.getImageVersionString()
		AboutText += ImageVersion + "\n"
		EnigmaVersion = _("GUI Build: ") + about.getEnigmaVersionString() + "\n"
		self["EnigmaVersion"] = StaticText(EnigmaVersion)
		FlashDate = _("Flashed: ") + about.getFlashDateString()
		self["FlashDate"] = StaticText(FlashDate)
		AboutText += FlashDate + "\n"

		AboutHeader = _("About") + " " + BoxName
		self["AboutHeader"] = StaticText(AboutHeader)

		GStreamerVersion = about.getGStreamerVersionString().replace("GStreamer", "")
		self["GStreamerVersion"] = StaticText(GStreamerVersion)

		ffmpegVersion = about.getffmpegVersionString()
		self["ffmpegVersion"] = StaticText(ffmpegVersion)

		player = None

		if os.path.isfile('/var/lib/opkg/info/enigma2-plugin-systemplugins-servicemp3.list'):
			if GStreamerVersion:
				player = _("Media player") + ": Gstreamer, " + _("version") + " " + GStreamerVersion
		if os.path.isfile('/var/lib/opkg/info/enigma2-plugin-systemplugins-servicehisilicon.list'):
			if os.path.isdir("/usr/lib/hisilicon") and glob.glob("/usr/lib/hisilicon/libavcodec.so.*"):
				player = _("Media player") + ": ffmpeg, " + _("Hardware Accelerated")
			elif ffmpegVersion and ffmpegVersion[0].isdigit():
				player = _("Media player") + ": ffmpeg, " + _("version") + " " + ffmpegVersion

		if player is None:
				player = _("Media player") + ": " + _("Not Installed")

		AboutText += player + "\n"

		CPUspeed = _("Speed: ") + about.getCPUSpeedString()
		self["CPUspeed"] = StaticText(CPUspeed)
		#AboutText += "(" + about.getCPUSpeedString() + ")\n"

		ChipsetInfo = _("Chipset: ") + about.getChipSetString()
		self["ChipsetInfo"] = StaticText(ChipsetInfo)
		AboutText += ChipsetInfo + "\n"

		if boxtype == 'gbquad4k' or boxtype == 'gbue4k' or boxtype == 'gbx34k':
			def strip_non_ascii(boltversion):
				''' Returns the string without non ASCII characters'''
				stripped = (c for c in boltversion if 0 < ord(c) < 127)
				return ''.join(stripped)
			boltversion = str(popen('cat /sys/firmware/devicetree/base/bolt/tag').read().strip())
			boltversion = strip_non_ascii(boltversion)
			AboutText += _("Bolt") + ":" + boltversion + "\n"
			self["BoltVersion"] = StaticText(boltversion)

		AboutText += _("Enigma (re)starts: %d\n") % config.misc.startCounter.value

		fp_version = getFPVersion()
		if fp_version != None and fp_version not in (0, "0"):
			fp_version = _("Frontprocessor version: %s") % fp_version
			#AboutText += fp_version +"\n"
		self["FPVersion"] = StaticText(fp_version)

		AboutText += "\n"

		KernelVersion = _("Kernel version: ") + about.getKernelVersionString()
		self["KernelVersion"] = StaticText(KernelVersion)
		AboutText += KernelVersion + "\n"

		if getMachineBuild() in ('gb7252', 'gb72604'):
			b = popen('cat /proc/stb/info/version').read().strip()
			driverdate = str(b[0:4] + '-' + b[4:6] + '-' + b[6:8] + ' ' + b[8:10] + ':' + b[10:12] + ':' + b[12:14])
			AboutText += _("DVB drivers: ") + driverdate + "\n"
		else:
			AboutText += _("DVB drivers: ") + self.realDriverDate() + "\n"
			#AboutText += _("DVB drivers: ") + about.getDriverInstalledDate() + "\n"


		EnigmaSkin = _('Skin & Resolution: %s (%sx%s)') % (config.skin.primary_skin.value.split('/')[0], getDesktop(0).size().width(), getDesktop(0).size().height())
		self["EnigmaSkin"] = StaticText(EnigmaSkin)
		AboutText += EnigmaSkin + "\n"

		AboutText += _("Python version: ") + about.getPythonVersionString() + "\n"
		AboutText += _("Enigma2 debug level:\t%d") % eGetEnigmaDebugLvl() + "\n"

		twisted = popen('opkg list-installed  |grep -i python3-twisted-core').read().strip().split(' - ')[1]
		AboutText += "Python-Twisted: " + str(twisted) + "\n"

		self["TunerHeader"] = StaticText(_("Detected NIMs:"))
		AboutText += "\n" + _("Detected NIMs:") + "\n"

		nims = nimmanager.nimListCompressed()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			AboutText += nims[count] + "\n"

		mounts = getProcMounts()

		self["StorageHeader"] = StaticText(_("Internal flash storage:"))
		AboutText += "\n" + _("Internal flash storage:") + "\n"

		storageinfo = ""
		for partition in harddiskmanager.getMountedPartitions(False, mounts):
			if partition.mountpoint != '/':
				continue
			free=(("%s MB" % (partition.free()//(1024**2)) if partition.free()//(1024**2) <= 1024 else ("%.2f GB" % (partition.free()/(1024**3)))))
			total=(("%s MB" % (partition.total()//(1024**2)) if partition.total()//(1024**2) <= 1024 else ("%.2f GB" % (partition.total()/(1024**3)))))
			storageinfo += _("Free: %s/%s\n") % (free, total)
			storageinfo += _("Filesystem: %s\n") % partition.filesystem()
			storageinfo += "\n"
		AboutText += storageinfo

		self["HDDHeader"] = StaticText(_("Detected storage devices:"))
		AboutText += _("Detected storage devices:") + "\n"

		hddinfo = ""
		for partition in harddiskmanager.getMountedPartitions(False, mounts):
			if partition.mountpoint == '/':
				continue
			hddinfo += "%s:\n" % (partition.description)
			hddinfo += _("Mountpoint: %s (%s)\n") % (partition.mountpoint,partition.device)
			free=(("%s MB" % (partition.free()//(1024**2)) if partition.free()//(1024**2) <= 1024 else ("%.2f GB" % (partition.free()/(1024**3)))))
			total=(("%s MB" % (partition.total()//(1024**2)) if partition.total()//(1024**2) <= 1024 else ("%.2f GB" % (partition.total()/(1024**3)))))
			hddinfo += _("Free: %s/%s\n") % (free, total)
			hddinfo += _("Filesystem: %s\n") % partition.filesystem()
			hddinfo += "\n"
		if hddinfo == "":
			hddinfo = _("none")
			hddinfo += "\n"
		AboutText += hddinfo

		AboutText += _("Uptime") + ": " + about.getBoxUptime()

		if BoxInfo.getItem("HDMICEC") and config.hdmicec.enabled.value:
			address = config.hdmicec.fixed_physical_address.value if config.hdmicec.fixed_physical_address.value != "0.0.0.0" else _("not set")
			AboutText += "\n\n" + _("HDMI-CEC address") + ": " + address

		self["AboutScrollLabel"] = ScrollLabel(AboutText)
		self["key_green"] = Button(_("Translations"))
		self["key_red"] = Button(_("Latest Commits"))
		self["key_yellow"] = Button(_("Troubleshoot"))
		self["key_blue"] = Button(_("Memory Info"))
		self["key_info"] = StaticText(_("Contact Info"))
		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"red": self.showCommits,
				"green": self.showTranslationInfo,
				"blue": self.showMemoryInfo,
				"info": self.showContactInfo,
				"yellow": self.showTroubleshoot,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self["AboutScrollLabel"].pageUp,
				"right": self["AboutScrollLabel"].pageDown
			})

	def showTranslationInfo(self):
		self.session.open(TranslationInfo)

	def showContactInfo(self):
		self.session.open(ContactInfo)

	def showCommits(self):
		self.session.open(CommitInfo)

	def showMemoryInfo(self):
		self.session.open(MemoryInfo)

	def realDriverDate(self):
		realdate = about.getDriverInstalledDate()
		try:
			y = popen('lsmod').read().strip()
			if 'dvb' in y:
				drivername = 'dvb'
				b = popen('modinfo ' + drivername + ' |grep -i version').read().strip().split()[1][:14]
				realdate = str(b[0:4] + '-' + b[4:6] + '-' + b[6:8] + ' ' + b[8:10] + ':' + b[10:12] + ':' + b[12:14])
		except:
			realdate = about.getDriverInstalledDate()
		return realdate

	def showTroubleshoot(self):
		self.session.open(Troubleshoot)


class TranslationInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Translation"))
		# don't remove the string out of the _(), or it can't be "translated" anymore.
		# TRANSLATORS: Add here whatever should be shown in the "translator" about screen, up to 6 lines (use \n for newline)
		# Don't translate TRANSLATOR_INFO to show '(N/A)'
		info = _("TRANSLATOR_INFO")
		if info == "TRANSLATOR_INFO":
			info = "(N/A)"

		infolines = _("").split("\n")
		infomap = {}
		for x in infolines:
			l = x.split(': ')
			if len(l) != 2:
				continue
			(type, value) = l
			infomap[type] = value
		self["actions"] = ActionMap(["SetupActions"], {"cancel": self.close, "ok": self.close})

		translator_name = infomap.get("Language-Team", "none")
		if translator_name == "none":
			translator_name = infomap.get("Last-Translator", "")

		linfo = ""
		linfo += _("Translations Info") + ":" + "\n\n"
		linfo += _("Project") + ":" + infomap.get("Project-Id-Version", "") + "\n"
		linfo += _("Language") + ":" + infomap.get("Language", "") + "\n"
		print(infomap.get("Language-Team", ""))
		if infomap.get("Language-Team", "") == "" or infomap.get("Language-Team", "") == "none":
			linfo += _("Language Team") + ":" + "n/a" + "\n"
		else:
			linfo += _("Language Team") + ":" + infomap.get("Language-Team", "") + "\n"
		linfo += _("Last Translator") + ":" + translator_name + "\n"
		linfo += "\n"
		linfo += _("Source Charset") + ":" + infomap.get("X-Poedit-SourceCharset", "") + "\n"
		linfo += _("Content Type") + ":" + infomap.get("Content-Type", "") + "\n"
		linfo += _("Content Encoding") + ":" + infomap.get("Content-Transfer-Encoding", "") + "\n"
		linfo += _("MIME Version") + ":" + infomap.get("MIME-Version", "") + "\n"
		linfo += "\n"
		linfo += _("POT-Creation Date") + ":" + infomap.get("POT-Creation-Date", "") + "\n"
		linfo += _("Revision Date") + ":" + infomap.get("PO-Revision-Date", "") + "\n"
		linfo += "\n"
		linfo += _("Generator") + ":" + infomap.get("X-Generator", "") + "\n"

		if infomap.get("Report-Msgid-Bugs-To", "") != "":
			linfo += _("Report Msgid Bugs To") + ":" + infomap.get("Report-Msgid-Bugs-To", "") + "\n"
		else:
			linfo += _("Report Msgid Bugs To") + ":" + "teamblue@online.de" + "\n"
		linfo += "\n"
		linfo += _("Translator comment") + ":" + "\n"
		linfo += (info)
		self["AboutScrollLabel"] = ScrollLabel(linfo)

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})


class CommitInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Latest Commits"))
		self.skinName = ["CommitInfo", "About"]
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"))
		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"left": self.left,
				"right": self.right,
				"deleteBackward": self.left,
				"deleteForward": self.right
			})

		self["key_red"] = Button(_("Cancel"))

		# get the branch to display from the Enigma version
		try:
			branch = "?sha=" + about.getEnigmaVersionString().split("(")[1].split(")")[0].lower()
		except:
			branch = ""
		branch_e2plugins = "?sha=python3"

		self.project = 0
		self.projects = [
			#("organisation",  "repository",           "readable name",                "branch", "github/gitlab"),
			("teamblue-e2", "enigma2", "teamBlue Enigma2", ("%s-dev" % BoxInfo.getItem('imageversion') if BoxInfo.getItem('imagetype') == "DEV" else BoxInfo.getItem('imageversion')), "github"),
			("teamblue-e2", "skin", "teamBlue Skin GigaBlue Pax", "master", "github"),
			("oe-alliance", "oe-alliance-core", "OE Alliance Core", BoxInfo.getItem('oe').split()[1], "github"),
			("oe-alliance", "oe-alliance-plugins", "OE Alliance Plugins", "master", "github"),
			("oe-alliance", "enigma2-plugins", "OE Alliance Enigma2 Plugins", "master", "github")
		]
		self.cachedProjects = {}
		self.Timer = eTimer()
		self.Timer.callback.append(self.readGithubCommitLogs)
		self.Timer.start(50, True)

	def readGithubCommitLogs(self):
		if self.projects[self.project][4] == "github":
			url = 'https://api.github.com/repos/%s/%s/commits?sha=%s' % (self.projects[self.project][0], self.projects[self.project][1], self.projects[self.project][3])
		if self.projects[self.project][4] == "gitlab":
			url1 = 'https://gitlab.com/api/v4/projects/%s' % (self.projects[self.project][0])
			url2 = '%2F'
			url3 = '%s/repository/commits?ref_name=%s' % (self.projects[self.project][1], self.projects[self.project][3])
			url = url1 + url2 + url3
			# print "[About] url: ", url
		commitlog = ""
		from datetime import datetime
		from json import loads
		from urllib.request import urlopen
		if self.projects[self.project][4] == "github":
			try:
				commitlog += 80 * '-' + '\n'
				commitlog += self.projects[self.project][2] + ' - ' + self.projects[self.project][1] + ' - branch ' + self.projects[self.project][3] + '\n'
				commitlog += 'URL: https://github.com/' + self.projects[self.project][0] + '/' + self.projects[self.project][1] + '/tree/' + self.projects[self.project][3] + '\n'
				commitlog += 80 * '-' + '\n'
				for c in loads(urlopen(url, timeout=5).read()):
					creator = c['commit']['author']['name']
					title = c['commit']['message']
					date = datetime.strptime(c['commit']['committer']['date'], '%Y-%m-%dT%H:%M:%SZ').strftime('%x %X')
					if title.startswith("Merge "):
						pass
					else:
						commitlog += date + ' ' + creator + '\n' + title + 2 * '\n'
				self.cachedProjects[self.projects[self.project][2]] = commitlog
			except:
				commitlog += _("Currently the commit log cannot be retrieved - please try later again")
		if self.projects[self.project][4] == "gitlab":
			try:
				commitlog += 80 * '-' + '\n'
				commitlog += self.projects[self.project][2] + ' - ' + self.projects[self.project][1] + ' - branch ' + self.projects[self.project][3] + '\n'
				commitlog += 'URL: https://gitlab.com/' + self.projects[self.project][0] + '/' + self.projects[self.project][1] + '/tree/' + self.projects[self.project][3] + '\n'
				commitlog += 80 * '-' + '\n'
				for c in loads(urlopen(url, timeout=5).read()):
					creator = c['author_name']
					title = c['message']
					date = datetime.strptime(c['committed_date'], '%Y-%m-%dT%H:%M:%S.000+02:00').strftime('%x %X')
					if title.startswith("Merge "):
						pass
					else:
						commitlog += date + ' ' + creator + '\n' + title + '\n'
				self.cachedProjects[self.projects[self.project][2]] = commitlog
			except:
				commitlog += _("Currently the commit log cannot be retrieved - please try later again")
		self["AboutScrollLabel"].setText(commitlog)

	def updateCommitLogs(self):
		if self.projects[self.project][2] in self.cachedProjects:
			self["AboutScrollLabel"].setText(self.cachedProjects[self.projects[self.project][2]])
		else:
			self["AboutScrollLabel"].setText(_("Please wait"))
			self.Timer.start(50, True)

	def left(self):
		self.project = self.project == 0 and len(self.projects) - 1 or self.project - 1
		self.updateCommitLogs()

	def right(self):
		self.project = self.project != len(self.projects) - 1 and self.project + 1 or 0
		self.updateCommitLogs()


class ContactInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["SetupActions"], {"cancel": self.close, "ok": self.close})
		self.setTitle(_("Contact info"))
		self["manufacturerinfo"] = StaticText(self.getManufacturerinfo())

	def getManufacturerinfo(self):
		minfo = "teamBlue\n"
		minfo += "http://teamblue.tech\n"
		return minfo


class MemoryInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.close,
				"ok": self.getMemoryInfo,
				"green": self.getMemoryInfo,
				"blue": self.clearMemory,
			})
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Refresh"))
		self["key_blue"] = Label(_("Clear"))
		self['lmemtext'] = Label()
		self['lmemvalue'] = Label()
		self['rmemtext'] = Label()
		self['rmemvalue'] = Label()
		self['pfree'] = Label()
		self['pused'] = Label()
		self["slide"] = ProgressBar()
		self["slide"].setValue(100)
		self["params"] = MemoryInfoSkinParams()
		self.setTitle(_("MemoryInfo - only for Developers"))
		self['info'] = Label(_("This info is for developers only.\nIt is not important for a normal user.\nPlease - do not panic on any displayed suspicious information!"))
		self.onLayoutFinish.append(self.getMemoryInfo)

	def getMemoryInfo(self):
		try:
			ltext = rtext = ""
			lvalue = rvalue = ""
			mem = 1
			free = 0
			rows_in_column = self["params"].rows_in_column
			for i, line in enumerate(open('/proc/meminfo', 'r')):
				s = line.strip().split(None, 2)
				if len(s) == 3:
					name, size, units = s
				elif len(s) == 2:
					name, size = s
					units = ""
				else:
					continue
				if name.startswith("MemTotal"):
					mem = int(size)
				if name.startswith("MemFree") or name.startswith("Buffers") or name.startswith("Cached"):
					free += int(size)
				if i < rows_in_column:
					ltext += "".join((name, "\n"))
					lvalue += "".join((size, " ", units, "\n"))
				else:
					rtext += "".join((name, "\n"))
					rvalue += "".join((size, " ", units, "\n"))
			self['lmemtext'].setText(ltext)
			self['lmemvalue'].setText(lvalue)
			self['rmemtext'].setText(rtext)
			self['rmemvalue'].setText(rvalue)
			self["slide"].setValue(int(100.0 * (mem - free) / mem + 0.25))
			self['pfree'].setText("%.1f %s" % (100. * free / mem, '%'))
			self['pused'].setText("%.1f %s" % (100. * (mem - free) / mem, '%'))
		except Exception as e:
			print("[About] getMemoryInfo FAIL:", e)

	def clearMemory(self):
		eConsoleAppContainer().execute("sync")
		open("/proc/sys/vm/drop_caches", "w").write("3")
		self.getMemoryInfo()


class MemoryInfoSkinParams(GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.rows_in_column = applySkinFactor(25)

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "rowsincolumn":
					self.rows_in_column = parseScale(value)
			self.skinAttributes = attribs
		return GUIComponent.applySkin(self, desktop, screen)

	GUI_WIDGET = eLabel


class SystemNetworkInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Network Information"))
		self.skinName = ["SystemNetworkInfo", "WlanStatus"]
		self["LabelBSSID"] = StaticText()
		self["LabelESSID"] = StaticText()
		self["LabelQuality"] = StaticText()
		self["LabelSignal"] = StaticText()
		self["LabelBitrate"] = StaticText()
		self["LabelEnc"] = StaticText()
		self["BSSID"] = StaticText()
		self["ESSID"] = StaticText()
		self["quality"] = StaticText()
		self["signal"] = StaticText()
		self["bitrate"] = StaticText()
		self["enc"] = StaticText()

		self["IFtext"] = StaticText()
		self["IF"] = StaticText()

		self.iface = None
		self.createscreen()
		self.iStatus = None

		if iNetwork.isWirelessInterface(self.iface):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
				self.iStatus = iStatus
			except:
				pass
			self.resetList()
			self.onClose.append(self.cleanup)
		self.updateStatusbar()

		self["key_red"] = StaticText(_("Close"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown
			})

	def createscreen(self):
		self.AboutText = ""
		self.iface = "eth0"
		eth0 = about.getIfConfig('eth0')
		if 'addr' in eth0:
			self.iface = 'eth0'
		eth1 = about.getIfConfig('eth1')
		if 'addr' in eth1:
			self.iface = 'eth1'
		ra0 = about.getIfConfig('ra0')
		if 'addr' in ra0:
			self.iface = 'ra0'
		wlan0 = about.getIfConfig('wlan0')
		if 'addr' in wlan0:
			self.iface = 'wlan0'
		self.AboutText += iNetwork.getFriendlyAdapterName(self.iface) + ":" + iNetwork.getFriendlyAdapterDescription(self.iface) + "\n"

		def nameserver():
			nameserver = ""
			v4 = 0
			v6 = 0
			ns4 = ""
			ns6 = ""
			datei = open("/etc/resolv.conf", "r")
			for line in datei.readlines():
				line = line.strip()
				if "nameserver" in line:
					if line.count(".") == 3:
						v4 = v4 + 1
						ns4 += str(v4) + ".IPv4 Nameserver" + ":" + line.strip().replace("nameserver ", "") + "\n"
					if line.count(":") > 1 and line.count(":") < 8:
						v6 = v6 + 1
						ns6 += str(v6) + ".IPv6 Nameserver" + ":" + line.strip().replace("nameserver ", "") + "\n"
			nameserver = ns4 + ns6
			datei.close()
			return nameserver.strip()

		def domain():
			domain = ""
			for line in open('/etc/resolv.conf', 'r'):
				line = line.strip()
				if "domain" in line:
					domain += line.strip().replace("domain ", "")
					return domain
				else:
					domain = _("no domain name found")
					return domain

		def gateway():
			gateway = ""
			for line in popen('ip route show'):
				line = line.strip()
				if "default via " in line:
					line = line.split(' ')
					line = line[2]
					return line
				else:
					line = _("no gateway found")
					return line

		def netspeed():
			netspeed = ""
			for line in popen('ethtool eth0 |grep Speed', 'r'):
				line = line.strip().split(":")
				line = line[1].replace(' ', '')
				netspeed += line
				return str(netspeed)

		def netspeed_eth1():
			netspeed = ""
			for line in popen('ethtool eth1 |grep Speed', 'r'):
				line = line.strip().split(":")
				line = line[1].replace(' ', '')
				netspeed += line
				return str(netspeed)

		if 'addr' in eth0:
			if 'ifname' in eth0:
				self.AboutText += _('Interface: /dev/' + eth0['ifname'] + "\n")
			self.AboutText += _("Network Speed:") + netspeed() + "\n"
			if 'hwaddr' in eth0:
				self.AboutText += _("MAC:") + eth0['hwaddr'] + "\n"
			self.AboutText += "\n" + _("IP:") + eth0['addr'] + "\n"
			self.AboutText += _("Gateway:") + gateway() + "\n"
			self.AboutText += nameserver() + "\n"
			if 'netmask' in eth0:
				self.AboutText += _("Netmask:") + eth0['netmask'] + "\n"
			if 'brdaddr' in eth0:
				if eth0['brdaddr'] == "0.0.0.0":
					self.AboutText += _('Broadcast:') + _("DHCP is off") + "\n"
				else:
					self.AboutText += _('Broadcast:' + eth0['brdaddr'] + "\n")
			self.AboutText += _("Domain:") + domain() + "\n"
			self.iface = 'eth0'

		eth1 = about.getIfConfig('eth1')
		if 'addr' in eth1:
			if 'ifname' in eth1:
				self.AboutText += _('Interface:/dev/' + eth1['ifname'] + "\n")
			self.AboutText += _("NetSpeed:") + netspeed_eth1() + "\n"
			if 'hwaddr' in eth1:
				self.AboutText += _("MAC:") + eth1['hwaddr'] + "\n"
			self.AboutText += "\n" + _("IP:") + eth1['addr'] + "\n"
			self.AboutText += _("Gateway:") + gateway() + "\n"
			self.AboutText += nameserver() + "\n"
			if 'netmask' in eth1:
				self.AboutText += _("Netmask:") + eth1['netmask'] + "\n"
			if 'brdaddr' in eth1:
				if eth1['brdaddr'] == "0.0.0.0":
					self.AboutText += _('Broadcast:') + _("DHCP is off") + "\n"
				else:
					self.AboutText += _('Broadcast:' + eth1['brdaddr'] + "\n")
			self.AboutText += _("Domain:") + domain() + "\n"
			self.iface = 'eth1'

		ra0 = about.getIfConfig('ra0')
		if 'addr' in ra0:
			if 'ifname' in ra0:
				self.AboutText += _('Interface:/dev/') + ra0['ifname'] + "\n"
			self.AboutText += "\n" + _("IP:") + ra0['addr'] + "\n"
			if 'netmask' in ra0:
				self.AboutText += _("Netmask:") + ra0['netmask'] + "\n"
			if 'brdaddr' in ra0:
				self.AboutText += _("Broadcast:") + ra0['brdaddr'] + "\n"
			if 'hwaddr' in ra0:
				self.AboutText += _("MAC:") + ra0['hwaddr'] + "\n"
			self.iface = 'ra0'

		wlan0 = about.getIfConfig('wlan0')
		if 'addr' in wlan0:
			if 'ifname' in wlan0:
				self.AboutText += _('Interface:/dev/') + wlan0['ifname'] + "\n"
			if 'hwaddr' in wlan0:
				self.AboutText += _("MAC:") + wlan0['hwaddr'] + "\n"
			self.AboutText += "\n" + _("IP:") + wlan0['addr'] + "\n"
			self.AboutText += _("Gateway:") + gateway() + "\n"
			self.AboutText += nameserver() + "\n"
			if 'netmask' in wlan0:
				self.AboutText += _("Netmask:") + wlan0['netmask'] + "\n"
			if 'brdaddr' in wlan0:
				if wlan0['brdaddr'] == "0.0.0.0":
					self.AboutText += _('Broadcast:') + _("DHCP is off") + "\n"
				else:
					self.AboutText += _('Broadcast:') + wlan0['brdaddr'] + "\n"
			self.AboutText += _("Domain:") + domain() + "\n"
			self.iface = 'wlan0'

		#not use this , adapter make reset after  4GB (32bit restriction)
		#rx_bytes, tx_bytes = about.getIfTransferredData(self.iface)
		#self.AboutText += "\n" + _("Bytes received:") + "\t" + rx_bytes + '  (~'  + str(int(rx_bytes)/1024/1024)  + ' MB)'  + "\n"
		#self.AboutText += _("Bytes sent:") + "\t" + tx_bytes + '  (~'  + str(int(tx_bytes)/1024/1024)+ ' MB)'  + "\n"

		hostname = open('/proc/sys/kernel/hostname').read()
		self.AboutText += _("Hostname:") + hostname + "\n"
		self["AboutScrollLabel"] = ScrollLabel(self.AboutText)

	def cleanup(self):
		if self.iStatus:
			self.iStatus.stopWlanConsole()

	def resetList(self):
		if self.iStatus:
			self.iStatus.getDataForInterface(self.iface, self.getInfoCB)

	def getInfoCB(self, data, status):
		self.LinkState = None
		if data is not None:
			if data is True:
				if status is not None:
					if self.iface == 'wlan0' or self.iface == 'ra0':
						if status[self.iface]["essid"] == "off":
							essid = _("No Connection")
						else:
							essid = status[self.iface]["essid"]
						if status[self.iface]["accesspoint"] == "Not-Associated":
							accesspoint = _("Not-Associated")
							essid = _("No Connection")
						else:
							accesspoint = status[self.iface]["accesspoint"]
						if "BSSID" in self:
							self.AboutText += _('Access point:') + accesspoint + '\n'
						if "ESSID" in self:
							self.AboutText += _('SSID:') + essid + '\n'

						quality = status[self.iface]["quality"]
						if "quality" in self:
							self.AboutText += _('Link Quality:') + quality + '\n'

						if status[self.iface]["bitrate"] == '0':
							bitrate = _("Unsupported")
						else:
							bitrate = str(status[self.iface]["bitrate"]) + " Mb/s"
						if "bitrate" in self:
							self.AboutText += _('Bitrate:') + bitrate + '\n'

						signal = status[self.iface]["signal"]
						if "signal" in self:
							self.AboutText += _('Signal Strength: %d \n' % signal)

						if status[self.iface]["encryption"] == "off":
							if accesspoint == "Not-Associated":
								encryption = _("Disabled")
							else:
								encryption = _("Unsupported")
						else:
							encryption = _("Enabled")
						if "enc" in self:
							self.AboutText += _('Encryption:') + encryption + '\n'

						if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] is False:
							self.LinkState = False
						else:
							self.LinkState = True
						self["AboutScrollLabel"].setText(self.AboutText)

	def exit(self):
		self.close(True)

	def updateStatusbar(self):
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterDescription(self.iface) + " - " + iNetwork.getFriendlyAdapterName(self.iface))
		#self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		if iNetwork.isWirelessInterface(self.iface):
			try:
				self.iStatus.getDataForInterface(self.iface, self.getInfoCB)
			except:
				pass
		else:
			iNetwork.getLinkState(self.iface, self.dataAvail)

	def dataAvail(self, data):
		data = six.ensure_str(data)
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if 'Link detected:' in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False


class Troubleshoot(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Troubleshoot"))
		self["AboutScrollLabel"] = ScrollLabel(_("Please wait"))
		self["key_red"] = Button()
		self["key_green"] = Button()

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
			{
				"cancel": self.close,
				"up": self["AboutScrollLabel"].pageUp,
				"down": self["AboutScrollLabel"].pageDown,
				"moveUp": self["AboutScrollLabel"].homePage,
				"moveDown": self["AboutScrollLabel"].endPage,
				"left": self.left,
				"right": self.right,
				"red": self.red,
				"green": self.green,
			})

		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.appClosed)
		self.container.dataAvail.append(self.dataAvail)
		self.commandIndex = 0
		self.updateOptions()
		self.onLayoutFinish.append(self.run_console)

	def left(self):
		self.commandIndex = (self.commandIndex - 1) % len(self.commands)
		self.updateKeys()
		self.run_console()

	def right(self):
		self.commandIndex = (self.commandIndex + 1) % len(self.commands)
		self.updateKeys()
		self.run_console()

	def red(self):
		if self.commandIndex >= self.numberOfCommands:
			self.session.openWithCallback(self.removeAllLogfiles, MessageBox, _("Do you want to remove all the crash logfiles"), default=False)
		else:
			self.close()

	def green(self):
		if self.commandIndex >= self.numberOfCommands:
			try:
				os.remove(self.commands[self.commandIndex][4:])
			except:
				pass
			self.updateOptions()
		self.run_console()

	def removeAllLogfiles(self, answer):
		if answer:
			for fileName in self.getLogFilesList():
				try:
					os.remove(fileName)
				except:
					pass
			self.updateOptions()
			self.run_console()

	def appClosed(self, retval):
		if retval:
			self["AboutScrollLabel"].setText(_("Some error occurred - Please try later"))

	def dataAvail(self, data):
		data = six.ensure_str(data)
		self["AboutScrollLabel"].appendText(data)

	def run_console(self):
		self["AboutScrollLabel"].setText("")
		self.setTitle("%s - %s" % (_("Troubleshoot"), self.titles[self.commandIndex]))
		command = self.commands[self.commandIndex]
		if command == "boxinfo":
			text = ""
			for item in BoxInfo.getItemsList():
				text += '%s = %s %s%s' % (item, str(BoxInfo.getItem(item)), type(BoxInfo.getItem(item)), " [immutable]\n" if item in BoxInfo.getEnigmaInfoList() else "\n")
			self["AboutScrollLabel"].setText(text)
		elif command.startswith("cat "):
			try:
				self["AboutScrollLabel"].setText(open(command[4:], "r").read())
			except:
				self["AboutScrollLabel"].setText(_("Logfile does not exist anymore"))
		else:
			try:
				if self.container.execute(command):
					raise Exception("failed to execute: ", command)
			except Exception as e:
				self["AboutScrollLabel"].setText("%s\n%s" % (_("Some error occurred - Please try later"), e))

	def cancel(self):
		self.container.appClosed.remove(self.appClosed)
		self.container.dataAvail.remove(self.dataAvail)
		self.container = None
		self.close()

	def getDebugFilesList(self):
		return [x for x in sorted(glob.glob("%s/Enigma2-debug-*.log" % config.crash.debug_path.value), key=lambda x: os.path.isfile(x) and os.path.getmtime(x))]

	def getLogFilesList(self):
		home_root = "/home/root/enigma2_crash.log"
		tmp = "/tmp/enigma2_crash.log"
		return [x for x in sorted(glob.glob("/mnt/hdd/*.log"), key=lambda x: os.path.isfile(x) and os.path.getmtime(x))] + (os.path.isfile(home_root) and [home_root] or []) + (os.path.isfile(tmp) and [tmp] or [])

	def updateOptions(self):
		self.titles = ["dmesg", "ifconfig", "df", "top", "ps", "messages", "enigma info", "BoxInfo"]
		self.commands = ["dmesg", "ifconfig", "df -h", "top -n 1", "ps -l", "cat /var/volatile/log/messages", "cat /usr/lib/enigma.info", "boxinfo"]
		install_log = "/home/root/autoinstall.log"
		if os.path.isfile(install_log):
				self.titles.append("%s" % install_log)
				self.commands.append("cat %s" % install_log)
		self.numberOfCommands = len(self.commands)
		fileNames = self.getLogFilesList()
		if fileNames:
			totalNumberOfLogfiles = len(fileNames)
			logfileCounter = 1
			for fileName in reversed(fileNames):
				self.titles.append("logfile %s (%s/%s)" % (fileName, logfileCounter, totalNumberOfLogfiles))
				self.commands.append("cat %s" % (fileName))
				logfileCounter += 1
		fileNames = self.getDebugFilesList()
		if fileNames:
			totalNumberOfLogfiles = len(fileNames)
			logfileCounter = 1
			for fileName in reversed(fileNames):
				self.titles.append("debug log %s (%s/%s)" % (fileName, logfileCounter, totalNumberOfLogfiles))
				self.commands.append("tail -n 2500 %s" % (fileName))
				logfileCounter += 1
		self.commandIndex = min(len(self.commands) - 1, self.commandIndex)
		self.updateKeys()

	def updateKeys(self):
		self["key_red"].setText(_("Cancel") if self.commandIndex < self.numberOfCommands else _("Remove all logfiles"))
		self["key_green"].setText(_("Refresh") if self.commandIndex < self.numberOfCommands else _("Remove this logfile"))
