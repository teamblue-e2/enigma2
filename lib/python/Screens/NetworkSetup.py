from os import path, unlink, system
import commands
import string
from random import Random
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Components.Network import iNetwork
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.SystemInfo import SystemInfo
from Components.Label import Label, MultiColorLabel
from Components.Pixmap import Pixmap, MultiPixmap
from Components.MenuList import MenuList
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigText, ConfigPassword, ConfigSelection, ConfigMacText
from Components.ConfigList import ConfigListScreen
from Components.PluginComponent import plugins
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Tools.Directories import resolveFilename, fileExists, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from Plugins.Plugin import PluginDescriptor
from enigma import eTimer, eConsoleAppContainer
from boxbranding import getBoxType


class NetworkAdapterSelection(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Select a network adapter"))
		self.wlan_errortext = _("No working wireless network adapter found.\nPlease verify that you have attached a compatible WLAN device and your network is configured correctly.")
		self.lan_errortext = _("No working local network adapter found.\nPlease verify that you have attached a network cable and your network is configured correctly.")
		self.oktext = _("Press OK on your remote control to continue.")
		self.edittext = _("Press OK to edit the settings.")
		self.defaulttext = _("Press yellow to set this interface as default interface.")
		self.restartLanRef = None

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["introduction"] = StaticText(self.edittext)

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("Exit network interface list")),
			"ok": (self.okbuttonClick, _("Select interface")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("Exit network interface list")),
			"green": (self.okbuttonClick, _("Select interface")),
			"blue": (self.openNetworkWizard, _("Use the network wizard to configure selected network adapter")),
			})

		self["DefaultInterfaceAction"] = HelpableActionMap(self, "ColorActions",
			{
			"yellow": (self.setDefaultInterface, [_("Set interface as default Interface"), _("* Only available if more than one interface is active.")]),
			})

		self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]

		if not self.adapters:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]

		if len(self.adapters) == 0:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]

		self.list = []
		self["list"] = List(self.list)
		self.updateList()

		if len(self.adapters) == 1:
			self.onFirstExecBegin.append(self.okbuttonClick)
		self.onClose.append(self.cleanup)

	def buildInterfaceList(self, iface, name, default, active):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "div-h.png"))
		defaultpng = None
		activepng = None
		description = None
		interfacepng = None

		if not iNetwork.isWirelessInterface(iface):
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/network_wired-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/network_wired-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/network_wired.png"))
		elif iNetwork.isWirelessInterface(iface):
			if active is True:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/network_wireless-active.png"))
			elif active is False:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/network_wireless-inactive.png"))
			else:
				interfacepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/network_wireless.png"))

		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			if default is True:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/button_blue.png"))
			elif default is False:
				defaultpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/button_blue_off.png"))
		if active is True:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "icons/lock_on.png"))
		elif active is False:
			activepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "icons/lock_error.png"))

		description = iNetwork.getFriendlyAdapterDescription(iface)

		return ((iface, name, description, interfacepng, defaultpng, activepng, divpng))

	def updateList(self):
		self.list = []
		default_gw = None
		iNetwork.getInterfaces()
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if num_configured_if >= 2:
			self["key_yellow"].setText(_("Default"))
			self["introduction"].setText(self.defaulttext)
			self["DefaultInterfaceAction"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["introduction"].setText(self.edittext)
			self["DefaultInterfaceAction"].setEnabled(False)

		if num_configured_if < 2 and path.exists("/etc/default_gw"):
			unlink("/etc/default_gw")

		if path.exists("/etc/default_gw"):
			fp = file('/etc/default_gw', 'r')
			result = fp.read()
			fp.close()
			default_gw = result

		for x in self.adapters:
			if x[1] == default_gw:
				default_int = True
			else:
				default_int = False
			if iNetwork.getAdapterAttribute(x[1], 'up') is True:
				active_int = True
			else:
				active_int = False
			self.list.append(self.buildInterfaceList(x[1], _(x[0]), default_int, active_int))

		if path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			self["key_blue"].setText(_("Network wizard"))
		self["list"].setList(self.list)

	def setDefaultInterface(self):
		selection = self["list"].getCurrent()
		num_if = len(self.list)
		old_default_gw = None
		num_configured_if = len(iNetwork.getConfiguredAdapters())
		if path.exists("/etc/default_gw"):
			fp = open('/etc/default_gw', 'r')
			old_default_gw = fp.read()
			fp.close()
		if num_configured_if > 1 and (not old_default_gw or old_default_gw != selection[0]):
			fp = open('/etc/default_gw', 'w+')
			fp.write(selection[0])
			fp.close()
			self.restartLan()
		elif old_default_gw and num_configured_if < 2:
			unlink("/etc/default_gw")
			self.restartLan()

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		if selection is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetupConfiguration, selection[0])

	def AdapterSetupClosed(self, *ret):
		if len(self.adapters) == 1:
			self.close()
		else:
			self.updateList()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)
		self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while we configure your network..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data is True:
			self.updateList()
			self.session.open(MessageBox, _("Finished configuring your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

	def openNetworkWizard(self):
		if path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			try:
				from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			except ImportError:
				self.session.open(MessageBox, _("The network wizard extension is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				selection = self["list"].getCurrent()
				if selection is not None:
					self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, selection[0])


class NameserverSetup(ConfigListScreen, HelpableScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Configure nameservers"))
		self.backupNameserverList = iNetwork.getNameserverList()[:]
		print "backup-list:", self.backupNameserverList

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Add"))
		self["key_yellow"] = StaticText(_("Delete"))

		self["introduction"] = StaticText(_("Press OK to activate the settings."))
		self.createConfig()

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.cancel, _("Exit nameserver configuration")),
			"ok": (self.ok, _("Activate current configuration")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.cancel, _("Exit nameserver configuration")),
			"green": (self.add, _("Add a nameserver entry")),
			"yellow": (self.remove, _("Remove a nameserver entry")),
			})

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.ok,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()

	def createConfig(self):
		self.nameservers = iNetwork.getNameserverList()
		self.nameserverEntries = [NoSave(ConfigIP(default=nameserver)) for nameserver in self.nameservers]

	def createSetup(self):
		self.list = []

		i = 1
		for x in self.nameserverEntries:
			self.list.append((_("Nameserver %d") % (i), x))
			i += 1

		self["config"].list = self.list

	def ok(self):
		iNetwork.clearNameservers()
		for nameserver in self.nameserverEntries:
			iNetwork.addNameserver(nameserver.value)
		iNetwork.writeNameserverConfig()
		self.close()

	def run(self):
		self.ok()

	def cancel(self):
		iNetwork.clearNameservers()
		print "backup-list:", self.backupNameserverList
		for nameserver in self.backupNameserverList:
			iNetwork.addNameserver(nameserver)
		self.close()

	def add(self):
		iNetwork.addNameserver([0, 0, 0, 0])
		self.createConfig()
		self.createSetup()

	def remove(self):
		print "currentIndex:", self["config"].getCurrentIndex()
		index = self["config"].getCurrentIndex()
		if index < len(self.nameservers):
			iNetwork.removeNameserver(self.nameservers[index])
			self.createConfig()
			self.createSetup()


class NetworkMacSetup(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		Screen.setTitle(self, _("MAC-adress settings"))
		self.curMac = self.getmac('eth0')
		self.getConfigMac = NoSave(ConfigMacText(default=self.curMac))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self["introduction"] = StaticText(_("Press OK to set the MAC-adress."))

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.cancel, _("Exit nameserver configuration")),
			"ok": (self.ok, _("Activate current configuration")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.cancel, _("Exit MAC-adress configuration")),
			"green": (self.ok, _("Activate MAC-adress configuration")),
			})

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.ok,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()

	def getmac(self, iface):
		mac = (0, 0, 0, 0, 0, 0)
		ifconfig = commands.getoutput("ifconfig " + iface + "| grep HWaddr | awk '{ print $5 }'").strip()
		if len(ifconfig) == 0:
			mac = "00:00:00:00:00:00"
		else:
			mac = ifconfig[:17]
		return mac

	def createSetup(self):
		self.list = []
		self.list.append((_("MAC-adress"), self.getConfigMac))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def ok(self):
		MAC = self.getConfigMac.getValue()
		f = open('/etc/enigma2/hwmac', 'w')
		f.write(MAC)
		f.close()
		route = commands.getoutput("route -n |grep UG | awk '{print $2}'")
		system('ifconfig eth0 down')
		system('ifconfig eth0 hw ether %s up' % MAC)
		system('route add default gw %s eth0' % route)
		self.close()

	def run(self):
		self.ok()

	def cancel(self):
		self.close()


class IPv6Setup(Screen, ConfigListScreen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		Screen.setTitle(self, _("IPv6 support"))

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_blue"] = StaticText(_("Restore inetd"))

		self["introduction"] = StaticText(_("Enable or disable Ipv6."))

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.cancel, _("Exit IPv6 configuration")),
			"ok": (self.ok, _("Activate IPv6 configuration")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.cancel, _("Exit IPv6 configuration")),
			"green": (self.ok, _("Activate IPv6 configuration")),
			"blue": (self.restoreinetdData, _("Restore inetd.conf")),
			})

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.ok,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)

		fp = open('/proc/sys/net/ipv6/conf/all/disable_ipv6', 'r')
		old_ipv6 = fp.read()
		fp.close()
		if int(old_ipv6) == 1:
			self.ipv6 = False
		else:
			self.ipv6 = True
		self.IPv6ConfigEntry = NoSave(ConfigYesNo(default=self.ipv6 or False))
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.IPv6Entry = (_("IPv6 support"), self.IPv6ConfigEntry)
		self.list.append(self.IPv6Entry)
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def restoreinetdData(self):
		inetdData = "# /etc/inetd.conf:  see inetd(music) for further informations.\n"
		inetdData += "#\n"
		inetdData += "# Internet server configuration database\n"
		inetdData += "#\n"
		inetdData += "# If you want to disable an entry so it isn't touched during\n"
		inetdData += "# package updates just comment it out with a single '#' character.\n"
		inetdData += "#\n"
		inetdData += "# <service_name> <sock_type> <proto> <flags> <user> <server_path> <args>\n"
		inetdData += "#\n"
		inetdData += "#:INTERNAL: Internal services\n"
		inetdData += "#echo	stream	tcp	nowait	root	internal\n"
		inetdData += "#echo	dgram	udp	wait	root	internal\n"
		inetdData += "#chargen	stream	tcp	nowait	root	internal\n"
		inetdData += "#chargen	dgram	udp	wait	root	internal\n"
		inetdData += "#discard	stream	tcp	nowait	root	internal\n"
		inetdData += "#discard	dgram	udp	wait	root	internal\n"
		inetdData += "#daytime	stream	tcp	nowait	root	internal\n"
		inetdData += "#daytime	dgram	udp	wait	root	internal\n"
		inetdData += "#time	stream	tcp	nowait	root	internal\n"
		inetdData += "#time	dgram	udp	wait	root	internal\n"
		if self.IPv6ConfigEntry.value == True:
			inetdData += "#ftp	stream	tcp6	nowait	root	/usr/sbin/vsftpd	vsftpd\n"
		else:
			inetdData += "#ftp	stream	tcp	nowait	root	/usr/sbin/vsftpd	vsftpd\n"
		inetdData += "#ftp	stream	tcp	nowait	root	ftpd	ftpd -w /\n"
		if self.IPv6ConfigEntry.value == True:
			inetdData += "#telnet	stream	tcp6	nowait	root	/usr/sbin/telnetd	telnetd\n"
		else:
			inetdData += "#telnet	stream	tcp	nowait	root	/usr/sbin/telnetd	telnetd\n"
		if fileExists('/usr/sbin/smbd') and self.IPv6ConfigEntry.value == True:
			inetdData += "#microsoft-ds	stream	tcp6	nowait	root	/usr/sbin/smbd	smbd\n"
		elif fileExists('/usr/sbin/smbd') and self.IPv6ConfigEntry.value == False:
			inetdData += "#microsoft-ds	stream	tcp	nowait	root	/usr/sbin/smbd	smbd\n"
		else:
			pass
		if fileExists('/usr/sbin/nmbd') and self.IPv6ConfigEntry.value == True:
			inetdData += "#netbios-ns	dgram	udp6	wait	root	/usr/sbin/nmbd	nmbd\n"
		elif fileExists('/usr/sbin/nmbd') and self.IPv6ConfigEntry.value == False:
			inetdData += "#netbios-ns	dgram	udp	wait	root	/usr/sbin/nmbd	nmbd\n"
		else:
			pass
		if fileExists('/usr/bin/streamproxy') and self.IPv6ConfigEntry.value == True:
			inetdData += "#8001	stream	tcp6	nowait	root	/usr/bin/streamproxy	streamproxy\n"
		elif fileExists('/usr/bin/streamproxy') and self.IPv6ConfigEntry.value == False:
			inetdData += "#8001	stream	tcp	nowait	root	/usr/bin/streamproxy	streamproxy\n"
		else:
			pass
		if fileExists('/usr/bin/transtreamproxy') and self.IPv6ConfigEntry.value == True:
			inetdData += "8002	stream	tcp6	nowait	root	/usr/bin/transtreamproxy	transtreamproxy\n"
		elif fileExists('/usr/bin/transtreamproxy') and self.IPv6ConfigEntry.value == False:
			inetdData += "8002	stream	tcp	nowait	root	/usr/bin/transtreamproxy	transtreamproxy\n"
		else:
			pass
		fd = file("/etc/inetd.conf", 'w')
		fd.write(inetdData)
		fd.close()
		self.session.open(MessageBox, _("Successfully restored /etc/inetd.conf!"), type=MessageBox.TYPE_INFO, timeout=10)

	def ok(self):
		ipv6 = '/etc/enigma2/ipv6'
		fp = open('/proc/sys/net/ipv6/conf/all/disable_ipv6', 'w')
		if self.IPv6ConfigEntry.value == False:
			fp.write("1")
			f = open(ipv6, 'w')
			f.write("1")
			f.close()
		else:
			fp.write("0")
			system("rm -R " + ipv6)
		fp.close()
		self.restoreinetdData()
		self.close()

	def run(self):
		self.ok()

	def cancel(self):
		self.close()


class AdapterSetup(ConfigListScreen, HelpableScreen, Screen):
	def __init__(self, session, networkinfo, essid=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Network setup"))
		if isinstance(networkinfo, (list, tuple)):
			self.iface = networkinfo[0]
			self.essid = networkinfo[1]
		else:
			self.iface = networkinfo
			self.essid = essid

		self.extended = None
		self.applyConfigRef = None
		self.finished_cb = None
		self.oktext = _("Press OK on your remote control to continue.")
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")

		self.createConfig()

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.keyCancel, _("exit network adapter configuration")),
			"ok": (self.keySave, _("activate network adapter configuration")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.keyCancel, _("exit network adapter configuration")),
			"green": (self.keySave, _("activate network adapter configuration")),
			"blue": (self.KeyBlue, _("open nameserver configuration")),
			})

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySave,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session)
		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

		self["DNS1text"] = StaticText(_("Primary DNS"))
		self["DNS2text"] = StaticText(_("Secondary DNS"))
		self["DNS1"] = StaticText()
		self["DNS2"] = StaticText()
		self["introduction"] = StaticText(_("Current settings:"))

		self["IPtext"] = StaticText(_("IP address"))
		self["Netmasktext"] = StaticText(_("Netmask"))
		self["Gatewaytext"] = StaticText(_("Gateway"))

		self["IP"] = StaticText()
		self["Mask"] = StaticText()
		self["Gateway"] = StaticText()

		self["Adaptertext"] = StaticText(_("Network:"))
		self["Adapter"] = StaticText()
		self["introduction2"] = StaticText(_("Press OK to activate the settings."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_blue"] = StaticText(_("Edit DNS"))

		self["VKeyIcon"] = Boolean(False)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()

	def layoutFinished(self):
		self["DNS1"].setText(self.primaryDNS.getText())
		self["DNS2"].setText(self.secondaryDNS.getText())
		if self.ipConfigEntry.getText() is not None:
			if self.ipConfigEntry.getText() == "0.0.0.0":
				self["IP"].setText(_("N/A"))
			else:
				self["IP"].setText(self.ipConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))
		if self.netmaskConfigEntry.getText() is not None:
			if self.netmaskConfigEntry.getText() == "0.0.0.0":
				self["Mask"].setText(_("N/A"))
			else:
				self["Mask"].setText(self.netmaskConfigEntry.getText())
		else:
			self["IP"].setText(_("N/A"))
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			if self.gatewayConfigEntry.getText() == "0.0.0.0":
				self["Gatewaytext"].setText(_("Gateway"))
				self["Gateway"].setText(_("N/A"))
			else:
				self["Gatewaytext"].setText(_("Gateway"))
				self["Gateway"].setText(self.gatewayConfigEntry.getText())
		else:
			self["Gateway"].setText("")
			self["Gatewaytext"].setText("")
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))

	def createConfig(self):
		self.InterfaceEntry = None
		self.dhcpEntry = None
		self.gatewayEntry = None
		self.hiddenSSID = None
		self.wlanSSID = None
		self.encryption = None
		self.encryptionType = None
		self.encryptionKey = None
		self.encryptionlist = None
		self.weplist = None
		self.wsconfig = None
		self.default = None

		if iNetwork.isWirelessInterface(self.iface):
			from Plugins.SystemPlugins.WirelessLan.Wlan import wpaSupplicant
			self.ws = wpaSupplicant()
			self.encryptionlist = []
			self.encryptionlist.append(("Unencrypted", _("Unencrypted")))
			self.encryptionlist.append(("WEP", "WEP"))
			self.encryptionlist.append(("WPA", "WPA"))
			if not path.exists("/tmp/bcm/" + self.iface):
				self.encryptionlist.append(("WPA/WPA2", "WPA/WPA2"))
			self.encryptionlist.append(("WPA2", "WPA2"))
			self.weplist = []
			self.weplist.append("ASCII")
			self.weplist.append("HEX")

			self.wsconfig = self.ws.loadConfig(self.iface)
			if self.essid is None:
				self.essid = self.wsconfig['ssid']

			config.plugins.wlan.hiddenessid = NoSave(ConfigYesNo(default=self.wsconfig['hiddenessid']))
			config.plugins.wlan.essid = NoSave(ConfigText(default=self.essid, visible_width=50, fixed_size=False))
			config.plugins.wlan.encryption = NoSave(ConfigSelection(self.encryptionlist, default=self.wsconfig['encryption']))
			config.plugins.wlan.wepkeytype = NoSave(ConfigSelection(self.weplist, default=self.wsconfig['wepkeytype']))
			config.plugins.wlan.psk = NoSave(ConfigPassword(default=self.wsconfig['key'], visible_width=50, fixed_size=False))

		self.activateInterfaceEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "up") or False))
		self.dhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp") or False))
		self.ipConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip")) or [0, 0, 0, 0])
		self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask") or [255, 0, 0, 0]))
		if iNetwork.getAdapterAttribute(self.iface, "gateway"):
			self.dhcpdefault = True
		else:
			self.dhcpdefault = False
		self.hasGatewayConfigEntry = NoSave(ConfigYesNo(default=self.dhcpdefault or False))
		self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway") or [0, 0, 0, 0]))
		nameserver = (iNetwork.getNameserverList() + [[0, 0, 0, 0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))

	def createSetup(self):
		if SystemInfo["WakeOnLAN"]:
			self.wolstartvalue = config.network.wol.value
		self.list = []
		self.InterfaceEntry = (_("Use interface"), self.activateInterfaceEntry)

		self.list.append(self.InterfaceEntry)
		if self.activateInterfaceEntry.value:
			self.dhcpEntry = (_("Use DHCP"), self.dhcpConfigEntry)
			self.list.append(self.dhcpEntry)
			if not self.dhcpConfigEntry.value:
				self.list.append((_('IP address'), self.ipConfigEntry))
				self.list.append((_('Netmask'), self.netmaskConfigEntry))
				self.gatewayEntry = (_('Use a gateway'), self.hasGatewayConfigEntry)
				self.list.append(self.gatewayEntry)
				if self.hasGatewayConfigEntry.value:
					self.list.append((_('Gateway'), self.gatewayConfigEntry))

			havewol = False
			if SystemInfo["WakeOnLAN"] and getBoxType() in ('gbquadplus', 'quadbox2400'):
				havewol = True
			if havewol and self.iface == 'eth0':
				self.list.append((_('Enable Wake On LAN'), config.network.wol))

			self.extended = None
			self.configStrings = None
			for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
				callFnc = p.__call__["ifaceSupported"](self.iface)
				if callFnc is not None:
					if "WlanPluginEntry" in p.__call__: # internally used only for WLAN Plugin
						self.extended = callFnc
						if "configStrings" in p.__call__:
							self.configStrings = p.__call__["configStrings"]
						isExistBcmWifi = path.exists("/tmp/bcm/" + self.iface)
						if not isExistBcmWifi:
							self.hiddenSSID = (_("Hidden network"), config.plugins.wlan.hiddenessid)
							self.list.append(self.hiddenSSID)
						self.wlanSSID = (_("Network name (SSID)"), config.plugins.wlan.essid)
						self.list.append(self.wlanSSID)
						self.encryption = (_("Encryption"), config.plugins.wlan.encryption)
						self.list.append(self.encryption)
						if not isExistBcmWifi:
							self.encryptionType = (_("Encryption key type"), config.plugins.wlan.wepkeytype)
						self.encryptionKey = (_("Encryption key"), config.plugins.wlan.psk)

						if config.plugins.wlan.encryption.value != "Unencrypted":
							if config.plugins.wlan.encryption.value == 'WEP':
								if not isExistBcmWifi:
									self.list.append(self.encryptionType)
							self.list.append(self.encryptionKey)
		self["config"].list = self.list

	def KeyBlue(self):
		self.session.openWithCallback(self.NameserverSetupClosed, NameserverSetup)

	def newConfig(self):
		if self["config"].getCurrent() == self.InterfaceEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.dhcpEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.gatewayEntry:
			self.createSetup()
		if iNetwork.isWirelessInterface(self.iface):
			if self["config"].getCurrent() == self.encryption:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keySave(self):
		self.hideInputHelp()
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.oldDHCPState = iNetwork.getAdapterAttribute(self.iface, 'dhcp')
		self.oldGatewayState = iNetwork.getAdapterAttribute(self.iface, "gateway")
		if self.oldGatewayState == None:
			oldstate = False
		else:
			oldstate = True
		self.longdesc = str(iNetwork.getFriendlyAdapterDescription(self.iface))[0:30]
		if self.dhcpConfigEntry.value == False:
			dhcpstat = _("disabled")
		else:
			dhcpstat = _("enabled")
		dhcpinfo = ""
		if self.activateInterfaceEntry.value == False:
			cardonoff = _("disabled")
			dhcpinfo = ""
		else:
			cardonoff = _("enabled")
			dhcpinfo = "DHCP: \t" + dhcpstat
		gwinfo = ""
		if self.dhcpConfigEntry.value == True:
			gwinfo = _("Gateway") + ":\t" + _("enabled") + " (" + _("automatic from DHCP") + ")"
		if self.hasGatewayConfigEntry.value == True:
			if self.dhcpConfigEntry.value == False:
				gwinfo = _("Gateway") + ":\t" + '%s.%s.%s.%s' % tuple(self.gatewayConfigEntry.value)
		if self.hasGatewayConfigEntry.value == False:
			if self.dhcpConfigEntry.value == False:
				gwinfo = _("Gateway") + ":\t" + _("disabled")
		if self.activateInterfaceEntry.value == False:
			gwinfo = ""

		netinfo = _("Device") + ":\t" + str(self.iface) + "\n"
		netinfo += _("Adapter") + ":\t" + self.longdesc + "\n" + _("Network") + ": \t" + cardonoff
		netinfo += "\n" + dhcpinfo
		netinfo += "\n" + gwinfo
		keySavego = self.session.openWithCallback(self.keySavego, MessageBox, (_("Are you sure you want to activate this network configuration?\n\n") + netinfo))
		keySavego.setTitle(self.longdesc)

	def keySavego(self, answer):
			if answer is True:
				config.network.save()
				self.keySaveConfirm(ret=True)
			else:
				if self.finished_cb:
					self.finished_cb()
				else:
					return

	def keySaveConfirm(self, ret=False):
		if ret:
			num_configured_if = len(iNetwork.getConfiguredAdapters())
			if num_configured_if >= 1:
				if self.iface in iNetwork.getConfiguredAdapters():
					self.applyConfig(True)
				else:
					self.session.openWithCallback(self.secondIfaceFoundCB, MessageBox, _("A second configured interface has been found.\n\nDo you want to disable the second network interface?"), default=True)
			else:
				self.applyConfig(True)
		else:
			self.keyCancel()

	def secondIfaceFoundCB(self, data):
		if data is False:
			self.applyConfig(True)
		else:
			configuredInterfaces = iNetwork.getConfiguredAdapters()
			for interface in configuredInterfaces:
				if interface == self.iface:
					continue
				iNetwork.setAdapterAttribute(interface, "up", False)
			iNetwork.deactivateInterface(configuredInterfaces, self.deactivateSecondInterfaceCB)

	def deactivateSecondInterfaceCB(self, data):
		if data is True:
			self.applyConfig(True)

	def applyConfig(self, ret=False):
		if ret:
			self.applyConfigRef = None
			iNetwork.setAdapterAttribute(self.iface, "up", self.activateInterfaceEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "dhcp", self.dhcpConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "ip", self.ipConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
			if self.hasGatewayConfigEntry.value:
				iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
			else:
				iNetwork.removeAdapterAttribute(self.iface, "gateway")

			if self.extended is not None and self.configStrings is not None:
				iNetwork.setAdapterAttribute(self.iface, "configStrings", self.configStrings(self.iface))
				self.ws.writeConfig(self.iface)

			if self.activateInterfaceEntry.value is False:
				iNetwork.deactivateInterface(self.iface, self.deactivateInterfaceCB)
				iNetwork.writeNetworkConfig()
				self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
			else:
				if self.oldInterfaceState is False:
					iNetwork.activateInterface(self.iface, self.deactivateInterfaceCB)
				else:
					iNetwork.deactivateInterface(self.iface, self.activateInterfaceCB)
				iNetwork.writeNetworkConfig()
				self.applyConfigRef = self.session.openWithCallback(self.applyConfigfinishedCB, MessageBox, _("Please wait for activation of your network configuration..."), type=MessageBox.TYPE_INFO, enable_input=False)
		else:
			self.keyCancel()

	def deactivateInterfaceCB(self, data):
		if data is True:
			self.applyConfigDataAvail(True)

	def activateInterfaceCB(self, data):
		if data is True:
			iNetwork.activateInterface(self.iface, self.applyConfigDataAvail)

	def applyConfigDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.applyConfigRef.close(True)

	def applyConfigfinishedCB(self, data):
		if data is True:
			if self.finished_cb:
				self.session.openWithCallback(lambda x: self.finished_cb(), MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				self.session.openWithCallback(self.ConfigfinishedCB, MessageBox, _("Your network configuration has been activated."), type=MessageBox.TYPE_INFO, timeout=10)

	def ConfigfinishedCB(self, data):
		if data is not None:
			if data is True:
				self.close('ok')

	def keyCancelConfirm(self, result):
		if not result:
			return
		if SystemInfo["WakeOnLAN"]:
			config.network.wol.setValue(self.wolstartvalue)
		if self.oldInterfaceState is False:
			iNetwork.deactivateInterface(self.iface, self.keyCancelCB)
		else:
			self.close('cancel')

	def keyCancel(self):
		self.hideInputHelp()
		if self["config"].isChanged() or (SystemInfo["WakeOnLAN"] and self.wolstartvalue != config.network.wol.value):
			self.session.openWithCallback(self.keyCancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
		else:
			self.close('cancel')

	def keyCancelCB(self, data):
		if data is not None:
			if data is True:
				self.close('cancel')

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.keySave()

	def NameserverSetupClosed(self, *ret):
		iNetwork.loadNameserverConfig()
		nameserver = (iNetwork.getNameserverList() + [[0, 0, 0, 0]] * 2)[0:2]
		self.primaryDNS = NoSave(ConfigIP(default=nameserver[0]))
		self.secondaryDNS = NoSave(ConfigIP(default=nameserver[1]))
		self.createSetup()
		self.layoutFinished()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()

	def hideInputHelp(self):
		current = self["config"].getCurrent()
		if current == self.wlanSSID:
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()
		elif current == self.encryptionKey and config.plugins.wlan.encryption.value is not "Unencrypted":
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()


class AdapterSetupConfiguration(Screen, HelpableScreen):
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Network configuration"))
		self.iface = iface
		self.restartLanRef = None
		self.LinkState = None
		self.mainmenu = self.genMainMenu()
		self["menulist"] = MenuList(self.mainmenu)
		self["key_red"] = StaticText(_("Close"))
		self["description"] = StaticText()
		self["IFtext"] = StaticText()
		self["IF"] = StaticText()
		self["Statustext"] = StaticText()
		self["statuspic"] = MultiPixmap()
		self["statuspic"].hide()

		self.oktext = _("Press OK on your remote control to continue.")
		self.reboottext = _("Your receiver will restart after pressing OK on your remote control.")
		self.errortext = _("No working wireless network interface found.\n Please verify that you have attached a compatible WLAN device or enable your local network interface.")
		self.missingwlanplugintxt = _("The wireless LAN plugin is not installed!\nPlease install it.")

		self["WizardActions"] = HelpableActionMap(self, "WizardActions",
			{
			"up": (self.up, _("move up to previous entry")),
			"down": (self.down, _("move down to next entry")),
			"left": (self.left, _("move up to first entry")),
			"right": (self.right, _("move down to last entry")),
			})

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("exit networkadapter setup menu")),
			"ok": (self.ok, _("select menu entry")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("exit networkadapter setup menu")),
			})

		self["actions"] = NumberActionMap(["WizardActions", "ShortcutActions"],
		{
			"ok": self.ok,
			"back": self.close,
			"up": self.up,
			"down": self.down,
			"red": self.close,
			"left": self.left,
			"right": self.right,
		}, -2)

		self.updateStatusbar()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def queryWirelessDevice(self, iface):
		try:
			from pythonwifi.iwlibs import Wireless
			import errno
		except ImportError:
			return False
		else:
			try:
				ifobj = Wireless(iface) # a Wireless NIC Object
				wlanresponse = ifobj.getAPaddr()
			except IOError, (error_no, error_str):
				if error_no in (errno.EOPNOTSUPP, errno.ENODEV, errno.EPERM):
					return False
				else:
					print "error: ", error_no, error_str
					return True
			else:
				return True

	def ok(self):
		self.cleanup()
		if self["menulist"].getCurrent()[1] == 'edit':
			if iNetwork.isWirelessInterface(self.iface):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
				except ImportError:
					self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
				else:
					if self.queryWirelessDevice(self.iface):
						self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
					else:
						self.showErrorMessage()	# Display Wlan not available Message
			else:
				self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface)
		if self["menulist"].getCurrent()[1] == 'test':
			self.session.open(NetworkAdapterTest, self.iface)
		if self["menulist"].getCurrent()[1] == 'dns':
			self.session.open(NameserverSetup)
		if self["menulist"].getCurrent()[1] == 'mac':
			self.session.open(NetworkMacSetup)
		if self["menulist"].getCurrent()[1] == 'ipv6':
			self.session.open(IPv6Setup)
		if self["menulist"].getCurrent()[1] == 'scanwlan':
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanScan
			except ImportError:
				self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
			else:
				if self.queryWirelessDevice(self.iface):
					self.session.openWithCallback(self.WlanScanClosed, WlanScan, self.iface)
				else:
					self.showErrorMessage()	# Display Wlan not available Message
		if self["menulist"].getCurrent()[1] == 'wlanstatus':
			try:
				from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
			except ImportError:
				self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
			else:
				if self.queryWirelessDevice(self.iface):
					self.session.openWithCallback(self.WlanStatusClosed, WlanStatus, self.iface)
				else:
					self.showErrorMessage()	# Display Wlan not available Message
		if self["menulist"].getCurrent()[1] == 'lanrestart':
			self.session.openWithCallback(self.restartLan, MessageBox, (_("Are you sure you want to restart your network interfaces?\n\n") + self.oktext))
		if self["menulist"].getCurrent()[1] == 'openwizard':
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.openWithCallback(self.AdapterSetupClosed, NetworkWizard, self.iface)
		if self["menulist"].getCurrent()[1][0] == 'extendedSetup':
			self.extended = self["menulist"].getCurrent()[1][2]
			self.extended(self.session, self.iface)

	def up(self):
		self["menulist"].up()
		self.loadDescription()

	def down(self):
		self["menulist"].down()
		self.loadDescription()

	def left(self):
		self["menulist"].pageUp()
		self.loadDescription()

	def right(self):
		self["menulist"].pageDown()
		self.loadDescription()

	def layoutFinished(self):
		idx = 0
		self["menulist"].moveToIndex(idx)
		self.loadDescription()

	def loadDescription(self):
		if self["menulist"].getCurrent()[1] == 'edit':
			self["description"].setText(_("Edit the network configuration of your receiver.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'test':
			self["description"].setText(_("Test the network configuration of your receiver.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'dns':
			self["description"].setText(_("Edit the nameserver configuration of your receiver.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'scanwlan':
			self["description"].setText(_("Scan your network for wireless access points and connect to them using your selected wireless device.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'wlanstatus':
			self["description"].setText(_("Shows the state of your wireless LAN connection.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'lanrestart':
			self["description"].setText(_("Restart your network connection and interfaces.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'openwizard':
			self["description"].setText(_("Use the network wizard to configure your network\n") + self.oktext)
		if self["menulist"].getCurrent()[1][0] == 'extendedSetup':
			self["description"].setText(_(self["menulist"].getCurrent()[1][1]) + self.oktext)
		if self["menulist"].getCurrent()[1] == 'mac':
			self["description"].setText(_("Set the MAC-adress of your receiver.\n") + self.oktext)
		if self["menulist"].getCurrent()[1] == 'ipv6':
			self["description"].setText(_("Enable/Disable IPv6 support of your receiver.\n") + self.oktext)

	def updateStatusbar(self, data=None):
		self.mainmenu = self.genMainMenu()
		self["menulist"].l.setList(self.mainmenu)
		self["IFtext"].setText(_("Network:"))
		self["IF"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Statustext"].setText(_("Link:"))

		if iNetwork.isWirelessInterface(self.iface):
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
			else:
				iStatus.getDataForInterface(self.iface, self.getInfoCB)
		else:
			iNetwork.getLinkState(self.iface, self.dataAvail)

	def doNothing(self):
		pass

	def genMainMenu(self):
		menu = []
		menu.append((_("Adapter settings"), "edit"))
		menu.append((_("Nameserver settings"), "dns"))
		menu.append((_("Network test"), "test"))
		menu.append((_("Restart network"), "lanrestart"))

		self.extended = None
		self.extendedSetup = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
			callFnc = p.__call__["ifaceSupported"](self.iface)
			if callFnc is not None:
				self.extended = callFnc
				if "WlanPluginEntry" in p.__call__: # internally used only for WLAN Plugin
					menu.append((_("Scan wireless networks"), "scanwlan"))
					if iNetwork.getAdapterAttribute(self.iface, "up"):
						menu.append((_("Show WLAN status"), "wlanstatus"))
				else:
					if "menuEntryName" in p.__call__:
						menuEntryName = p.__call__["menuEntryName"](self.iface)
					else:
						menuEntryName = _('Extended setup...')
					if "menuEntryDescription" in p.__call__:
						menuEntryDescription = p.__call__["menuEntryDescription"](self.iface)
					else:
						menuEntryDescription = _('Extended network setup plugin...')
					self.extendedSetup = ('extendedSetup', menuEntryDescription, self.extended)
					menu.append((menuEntryName, self.extendedSetup))

		if path.exists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")):
			menu.append((_("Network wizard"), "openwizard"))
		# CHECK WHICH BOXES NOW SUPPORT MAC-CHANGE VIA GUI
		if getBoxType() not in ('DUMMY') and self.iface == 'eth0':
			menu.append((_("Network MAC settings"), "mac"))
			# DISABLE IPv6 SUPPORT
			menu.append((_("Enable/Disable IPv6"), "ipv6"))

		return menu

	def AdapterSetupClosed(self, *ret):
		if ret is not None and len(ret):
			if ret[0] == 'ok' and (iNetwork.isWirelessInterface(self.iface) and iNetwork.getAdapterAttribute(self.iface, "up") is True):
				try:
					from Plugins.SystemPlugins.WirelessLan.plugin import WlanStatus
				except ImportError:
					self.session.open(MessageBox, self.missingwlanplugintxt, type=MessageBox.TYPE_INFO, timeout=10)
				else:
					if self.queryWirelessDevice(self.iface):
						self.session.openWithCallback(self.WlanStatusClosed, WlanStatus, self.iface)
					else:
						self.showErrorMessage()	# Display Wlan not available Message
			else:
				self.updateStatusbar()
		else:
			self.updateStatusbar()

	def WlanStatusClosed(self, *ret):
		if ret is not None and len(ret):
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()

	def WlanScanClosed(self, *ret):
		if ret[0] is not None:
			self.session.openWithCallback(self.AdapterSetupClosed, AdapterSetup, self.iface, ret[0])
		else:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			iStatus.stopWlanConsole()
			self.updateStatusbar()

	def restartLan(self, ret=False):
		if ret:
			iNetwork.restartNetwork(self.restartLanDataAvail)
			self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data is True:
			self.updateStatusbar()
			self.session.open(MessageBox, _("Finished restarting your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

	def dataAvail(self, data):
		self.LinkState = None
		for line in data.splitlines():
			line = line.strip()
			if 'Link detected:' in line:
				if "yes" in line:
					self.LinkState = True
				else:
					self.LinkState = False
		if self.LinkState:
			iNetwork.checkNetworkState(self.checkNetworkCB)
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()

	def showErrorMessage(self):
		self.session.open(MessageBox, self.errortext, type=MessageBox.TYPE_INFO, timeout=10)

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopDeactivateInterfaceConsole()
		iNetwork.stopActivateInterfaceConsole()
		iNetwork.stopPingConsole()
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
		except ImportError:
			pass
		else:
			iStatus.stopWlanConsole()

	def getInfoCB(self, data, status):
		self.LinkState = None
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] == False:
						self.LinkState = False
						self["statuspic"].setPixmapNum(1)
						self["statuspic"].show()
					else:
						self.LinkState = True
						iNetwork.checkNetworkState(self.checkNetworkCB)

	def checkNetworkCB(self, data):
		if iNetwork.getAdapterAttribute(self.iface, "up") is True:
			if self.LinkState is True:
				if data <= 2:
					self["statuspic"].setPixmapNum(0)
				else:
					self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
			else:
				self["statuspic"].setPixmapNum(1)
				self["statuspic"].show()
		else:
			self["statuspic"].setPixmapNum(1)
			self["statuspic"].show()


class NetworkAdapterTest(Screen):
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		self.iface = iface
		self.setTitle(_("Network test: ") + iNetwork.getFriendlyAdapterName(self.iface))
		self.oldInterfaceState = iNetwork.getAdapterAttribute(self.iface, "up")
		self.setLabels()
		self.onClose.append(self.cleanup)
		self.onHide.append(self.cleanup)

		self["updown_actions"] = NumberActionMap(["WizardActions", "ShortcutActions"],
		{
			"ok": self.KeyOK,
			"blue": self.KeyOK,
			"up": lambda: self.updownhandler('up'),
			"down": lambda: self.updownhandler('down'),

		}, -2)

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"red": self.cancel,
			"back": self.cancel,
		}, -2)
		self["infoshortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"red": self.closeInfo,
			"back": self.closeInfo,
		}, -2)
		self["shortcutsgreen"] = ActionMap(["ShortcutActions"],
		{
			"green": self.KeyGreen,
		}, -2)
		self["shortcutsgreen_restart"] = ActionMap(["ShortcutActions"],
		{
			"green": self.KeyGreenRestart,
		}, -2)
		self["shortcutsyellow"] = ActionMap(["ShortcutActions"],
		{
			"yellow": self.KeyYellow,
		}, -2)

		self["shortcutsgreen_restart"].setEnabled(False)
		self["updown_actions"].setEnabled(False)
		self["infoshortcuts"].setEnabled(False)
		self.onClose.append(self.delTimer)
		self.onLayoutFinish.append(self.layoutFinished)
		self.steptimer = False
		self.nextstep = 0
		self.activebutton = 0
		self.nextStepTimer = eTimer()
		self.nextStepTimer.callback.append(self.nextStepTimerFire)

	def cancel(self):
		if self.oldInterfaceState is False:
			iNetwork.setAdapterAttribute(self.iface, "up", self.oldInterfaceState)
			iNetwork.deactivateInterface(self.iface)
		self.close()

	def closeInfo(self):
		self["shortcuts"].setEnabled(True)
		self["infoshortcuts"].setEnabled(False)
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_red"].setText(_("Close"))

	def delTimer(self):
		del self.steptimer
		del self.nextStepTimer

	def nextStepTimerFire(self):
		self.nextStepTimer.stop()
		self.steptimer = False
		self.runTest()

	def updownhandler(self, direction):
		if direction == 'up':
			if self.activebutton >= 2:
				self.activebutton -= 1
			else:
				self.activebutton = 6
			self.setActiveButton(self.activebutton)
		if direction == 'down':
			if self.activebutton <= 5:
				self.activebutton += 1
			else:
				self.activebutton = 1
			self.setActiveButton(self.activebutton)

	def setActiveButton(self, button):
		if button == 1:
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(1) 		  # active
			self["AdapterInfo_Text"].setForegroundColorNum(2) # active
		if button == 2:
			self["AdapterInfo_Text"].setForegroundColorNum(1)
			self["AdapterInfo"].setPixmapNum(0)
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["NetworkInfo"].setPixmapNum(1) 		  # active
			self["NetworkInfo_Text"].setForegroundColorNum(2) # active
		if button == 3:
			self["NetworkInfo"].setPixmapNum(0)
			self["NetworkInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["DhcpInfo"].setPixmapNum(1) 		  # active
			self["DhcpInfo_Text"].setForegroundColorNum(2) 	  # active
		if button == 4:
			self["DhcpInfo"].setPixmapNum(0)
			self["DhcpInfo_Text"].setForegroundColorNum(1)
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["IPInfo"].setPixmapNum(1)			# active
			self["IPInfo_Text"].setForegroundColorNum(2)	# active
		if button == 5:
			self["IPInfo"].setPixmapNum(0)
			self["IPInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(0)
			self["EditSettings_Text"].setForegroundColorNum(0)
			self["DNSInfo"].setPixmapNum(1)			# active
			self["DNSInfo_Text"].setForegroundColorNum(2)	# active
		if button == 6:
			self["DNSInfo"].setPixmapNum(0)
			self["DNSInfo_Text"].setForegroundColorNum(1)
			self["EditSettingsButton"].setPixmapNum(1) 	   # active
			self["EditSettings_Text"].setForegroundColorNum(2) # active
			self["AdapterInfo"].setPixmapNum(0)
			self["AdapterInfo_Text"].setForegroundColorNum(1)

	def runTest(self):
		next = self.nextstep
		if next == 0:
			self.doStep1()
		elif next == 1:
			self.doStep2()
		elif next == 2:
			self.doStep3()
		elif next == 3:
			self.doStep4()
		elif next == 4:
			self.doStep5()
		elif next == 5:
			self.doStep6()
		self.nextstep += 1

	def doStep1(self):
		self.steptimer = True
		self.nextStepTimer.start(300)
		self["key_yellow"].setText(_("Stop test"))

	def doStep2(self):
		self["Adapter"].setText(iNetwork.getFriendlyAdapterName(self.iface))
		self["Adapter"].setForegroundColorNum(2)
		self["Adaptertext"].setForegroundColorNum(1)
		self["AdapterInfo_Text"].setForegroundColorNum(1)
		self["AdapterInfo_OK"].show()
		self.steptimer = True
		self.nextStepTimer.start(300)

	def doStep3(self):
		self["Networktext"].setForegroundColorNum(1)
		self["Network"].setText(_("Please wait..."))
		self.getLinkState(self.iface)
		self["NetworkInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def doStep4(self):
		self["Dhcptext"].setForegroundColorNum(1)
		if iNetwork.getAdapterAttribute(self.iface, 'dhcp') is True:
			self["Dhcp"].setForegroundColorNum(2)
			self["Dhcp"].setText(_("enabled"))
			self["DhcpInfo_Check"].setPixmapNum(0)
		else:
			self["Dhcp"].setForegroundColorNum(1)
			self["Dhcp"].setText(_("disabled"))
			self["DhcpInfo_Check"].setPixmapNum(1)
		self["DhcpInfo_Check"].show()
		self["DhcpInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def doStep5(self):
		self["IPtext"].setForegroundColorNum(1)
		self["IP"].setText(_("Please wait..."))
		iNetwork.checkNetworkState(self.NetworkStatedataAvail)

	def doStep6(self):
		self.steptimer = False
		self.nextStepTimer.stop()
		self["DNStext"].setForegroundColorNum(1)
		self["DNS"].setText(_("Please wait..."))
		iNetwork.checkDNSLookup(self.DNSLookupdataAvail)

	def KeyGreen(self):
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyGreenRestart(self):
		self.nextstep = 0
		self.layoutFinished()
		self["Adapter"].setText("")
		self["Network"].setText("")
		self["Dhcp"].setText("")
		self["IP"].setText("")
		self["DNS"].setText("")
		self["AdapterInfo_Text"].setForegroundColorNum(0)
		self["NetworkInfo_Text"].setForegroundColorNum(0)
		self["DhcpInfo_Text"].setForegroundColorNum(0)
		self["IPInfo_Text"].setForegroundColorNum(0)
		self["DNSInfo_Text"].setForegroundColorNum(0)
		self["shortcutsgreen_restart"].setEnabled(False)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(True)
		self["updown_actions"].setEnabled(False)
		self["key_yellow"].setText("")
		self["key_green"].setText("")
		self.steptimer = True
		self.nextStepTimer.start(1000)

	def KeyOK(self):
		self["infoshortcuts"].setEnabled(True)
		self["shortcuts"].setEnabled(False)
		if self.activebutton == 1: # Adapter Check
			self["InfoText"].setText(_("This test detects your configured LAN adapter."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 2: #LAN Check
			self["InfoText"].setText(_("This test checks whether a network cable is connected to your LAN adapter.\nIf you get a \"disconnected\" message:\n- verify that a network cable is attached\n- verify that the cable is not broken"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 3: #DHCP Check
			self["InfoText"].setText(_("This test checks whether your LAN adapter is set up for automatic IP address configuration with DHCP.\nIf you get a \"disabled\" message:\n - then your LAN adapter is configured for manual IP setup\n- verify thay you have entered the correct IP information in the adapter setup dialog.\nIf you get an \"enabeld\" message:\n-verify that you have a configured and working DHCP server in your network."))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 4: # IP Check
			self["InfoText"].setText(_("This test checks whether a valid IP address is found for your LAN adapter.\nIf you get a \"unconfirmed\" message:\n- no valid IP address was found\n- please check your DHCP, cabling and adapter setup"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 5: # DNS Check
			self["InfoText"].setText(_("This test checks for configured nameservers.\nIf you get a \"unconfirmed\" message:\n- please check your DHCP, cabling and adapter setup\n- if you configured your nameservers manually please verify your entries in the \"Nameserver\" configuration"))
			self["InfoTextBorder"].show()
			self["InfoText"].show()
			self["key_red"].setText(_("Back"))
		if self.activebutton == 6: # Edit Settings
			self.session.open(AdapterSetup, self.iface)

	def KeyYellow(self):
		self.nextstep = 0
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsyellow"].setEnabled(False)
		self["key_green"].setText(_("Restart test"))
		self["key_yellow"].setText("")
		self.steptimer = False
		self.nextStepTimer.stop()

	def layoutFinished(self):
		self["shortcutsyellow"].setEnabled(False)
		self["AdapterInfo_OK"].hide()
		self["NetworkInfo_Check"].hide()
		self["DhcpInfo_Check"].hide()
		self["IPInfo_Check"].hide()
		self["DNSInfo_Check"].hide()
		self["EditSettings_Text"].hide()
		self["EditSettingsButton"].hide()
		self["InfoText"].hide()
		self["InfoTextBorder"].hide()
		self["key_yellow"].setText("")

	def setLabels(self):
		self["Adaptertext"] = MultiColorLabel(_("LAN adapter"))
		self["Adapter"] = MultiColorLabel()
		self["AdapterInfo"] = MultiPixmap()
		self["AdapterInfo_Text"] = MultiColorLabel(_("Show info"))
		self["AdapterInfo_OK"] = Pixmap()

		if self.iface in iNetwork.wlan_interfaces:
			self["Networktext"] = MultiColorLabel(_("Wireless network"))
		else:
			self["Networktext"] = MultiColorLabel(_("Local network"))

		self["Network"] = MultiColorLabel()
		self["NetworkInfo"] = MultiPixmap()
		self["NetworkInfo_Text"] = MultiColorLabel(_("Show info"))
		self["NetworkInfo_Check"] = MultiPixmap()

		self["Dhcptext"] = MultiColorLabel(_("DHCP"))
		self["Dhcp"] = MultiColorLabel()
		self["DhcpInfo"] = MultiPixmap()
		self["DhcpInfo_Text"] = MultiColorLabel(_("Show info"))
		self["DhcpInfo_Check"] = MultiPixmap()

		self["IPtext"] = MultiColorLabel(_("IP address"))
		self["IP"] = MultiColorLabel()
		self["IPInfo"] = MultiPixmap()
		self["IPInfo_Text"] = MultiColorLabel(_("Show info"))
		self["IPInfo_Check"] = MultiPixmap()

		self["DNStext"] = MultiColorLabel(_("Nameserver"))
		self["DNS"] = MultiColorLabel()
		self["DNSInfo"] = MultiPixmap()
		self["DNSInfo_Text"] = MultiColorLabel(_("Show info"))
		self["DNSInfo_Check"] = MultiPixmap()

		self["EditSettings_Text"] = MultiColorLabel(_("Edit settings"))
		self["EditSettingsButton"] = MultiPixmap()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start test"))
		self["key_yellow"] = StaticText(_("Stop test"))

		self["InfoTextBorder"] = Pixmap()
		self["InfoText"] = Label()

	def getLinkState(self, iface):
		if iface in iNetwork.wlan_interfaces:
			try:
				from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
			except:
				self["Network"].setForegroundColorNum(1)
				self["Network"].setText(_("disconnected"))
				self["NetworkInfo_Check"].setPixmapNum(1)
				self["NetworkInfo_Check"].show()
			else:
				iStatus.getDataForInterface(self.iface, self.getInfoCB)
		else:
			iNetwork.getLinkState(iface, self.LinkStatedataAvail)

	def LinkStatedataAvail(self, data):
		for item in data.splitlines():
			if "Link detected:" in item:
				if "yes" in item:
					self["Network"].setForegroundColorNum(2)
					self["Network"].setText(_("connected"))
					self["NetworkInfo_Check"].setPixmapNum(0)
				else:
					self["Network"].setForegroundColorNum(1)
					self["Network"].setText(_("disconnected"))
					self["NetworkInfo_Check"].setPixmapNum(1)
				break
		else:
			self["Network"].setText(_("unknown"))
		self["NetworkInfo_Check"].show()

	def NetworkStatedataAvail(self, data):
		if data <= 2:
			self["IP"].setForegroundColorNum(2)
			self["IP"].setText(_("confirmed"))
			self["IPInfo_Check"].setPixmapNum(0)
		else:
			self["IP"].setForegroundColorNum(1)
			self["IP"].setText(_("unconfirmed"))
			self["IPInfo_Check"].setPixmapNum(1)
		self["IPInfo_Check"].show()
		self["IPInfo_Text"].setForegroundColorNum(1)
		self.steptimer = True
		self.nextStepTimer.start(300)

	def DNSLookupdataAvail(self, data):
		if data <= 2:
			self["DNS"].setForegroundColorNum(2)
			self["DNS"].setText(_("confirmed"))
			self["DNSInfo_Check"].setPixmapNum(0)
		else:
			self["DNS"].setForegroundColorNum(1)
			self["DNS"].setText(_("unconfirmed"))
			self["DNSInfo_Check"].setPixmapNum(1)
		self["DNSInfo_Check"].show()
		self["DNSInfo_Text"].setForegroundColorNum(1)
		self["EditSettings_Text"].show()
		self["EditSettingsButton"].setPixmapNum(1)
		self["EditSettings_Text"].setForegroundColorNum(2) # active
		self["EditSettingsButton"].show()
		self["key_yellow"].setText("")
		self["key_green"].setText(_("Restart test"))
		self["shortcutsgreen"].setEnabled(False)
		self["shortcutsgreen_restart"].setEnabled(True)
		self["shortcutsyellow"].setEnabled(False)
		self["updown_actions"].setEnabled(True)
		self.activebutton = 6

	def getInfoCB(self, data, status):
		if data is not None:
			if data is True:
				if status is not None:
					if status[self.iface]["essid"] == "off" or status[self.iface]["accesspoint"] == "Not-Associated" or status[self.iface]["accesspoint"] == False:
						self["Network"].setForegroundColorNum(1)
						self["Network"].setText(_("disconnected"))
						self["NetworkInfo_Check"].setPixmapNum(1)
						self["NetworkInfo_Check"].show()
					else:
						self["Network"].setForegroundColorNum(2)
						self["Network"].setText(_("connected"))
						self["NetworkInfo_Check"].setPixmapNum(0)
						self["NetworkInfo_Check"].show()

	def cleanup(self):
		iNetwork.stopLinkStateConsole()
		iNetwork.stopDNSConsole()
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
		except ImportError:
			pass
		else:
			iStatus.stopWlanConsole()


class NetworkPassword(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "NetworkPassword"
		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.selectionChanged)
		Screen.setTitle(self, _("Password setup"))

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Random password"))
		self["key_blue"] = StaticText("")

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "VirtualKeyboardActions"], {
			"red": self.close,
			"cancel": self.close,
			"green": self.SetPasswd,
			"save": self.SetPasswd,
			"yellow": self.newRandom,
			'showVirtualKeyboard': self.KeyText
			})

		self["description"] = Label()
		self['footnote'] = Label()
		self["VKeyIcon"] = Boolean(False)
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()

		self.user = "root"
		self.output_line = ""

		self.updateList()
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		item = self["config"].getCurrent()
		self["description"].setText(item[2])

	def newRandom(self):
		self.password.value = self.GeneratePassword()
		self["config"].invalidateCurrent()

	def updateList(self):
		self.password = NoSave(ConfigPassword(default=""))
		instructions = _("You must set a root password in order to be able to use network services,"
						" such as FTP, telnet or ssh.")
		self.list.append((_('New password'), self.password, instructions))
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def GeneratePassword(self):
		passwdChars = string.letters + string.digits
		passwdLength = 10
		return ''.join(Random().sample(passwdChars, passwdLength))

	def SetPasswd(self):
		self.hideHelpWindow()
		password = self.password.value
		if not password:
			self.session.openWithCallback(self.showHelpWindow, MessageBox, _("The password can not be blank."), MessageBox.TYPE_ERROR)
			return
		#print "[NetworkPassword] Changing the password for %s to %s" % (self.user,self.password)
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		retval = self.container.execute("echo -e '%s\n%s' | (passwd %s)" % (password, password, self.user))
		if retval:
			message = _("Unable to change password")
			self.session.openWithCallback(self.showHelpWindow, MessageBox, message, MessageBox.TYPE_ERROR)
		else:
			message = _("Password changed")
			self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=5)
			self.close()

	def showHelpWindow(self, ret=None):
		if self['config'].getCurrent() and isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			if self["config"].getCurrent()[1].help_window.instance is not None:
				self["config"].getCurrent()[1].help_window.show()

	def hideHelpWindow(self):
		if self['config'].getCurrent() and isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			if self["config"].getCurrent()[1].help_window.instance is not None:
				self["config"].getCurrent()[1].help_window.hide()

	def KeyText(self):
		if self['config'].getCurrent() and isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
			if self["config"].getCurrent()[1].help_window.instance is not None:
				self["config"].getCurrent()[1].help_window.hide()
			from Screens.VirtualKeyBoard import VirtualKeyBoard
			self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def VirtualKeyBoardCallback(self, callback=None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())
		self.showHelpWindow()

	def dataAvail(self, data):
		self.output_line += data
		while True:
			i = self.output_line.find('\n')
			if i == -1:
				break
			self.processOutputLine(self.output_line[:i + 1])
			self.output_line = self.output_line[i + 1:]

	def processOutputLine(self, line):
		if line.find('password: '):
			self.container.write("%s\n" % self.password.value)

	def runFinished(self, retval):
		del self.container.dataAvail[:]
		del self.container.appClosed[:]
		del self.container
		self.close()
