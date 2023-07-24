from Components.SystemInfo import SystemInfo
from Components.Console import Console
from Tools.Directories import fileHas, fileExists
import os
import glob
import tempfile
import subprocess

class tmp:
	dir = None


def getMultibootStartupDevice():
	tmp.dir = tempfile.mkdtemp(prefix="Multiboot")
	if SystemInfo["hasKexec"]: # kexec kernel multiboot
		bootList = ("/dev/mmcblk0p4", "/dev/mmcblk0p7", "/dev/mmcblk0p9")
	else: #legacy multiboot
		bootList = ("/dev/mmcblk0p1", "/dev/mmcblk1p1", "/dev/mmcblk0p3", "/dev/mmcblk0p4", "/dev/mtdblock2", "/dev/block/by-name/bootoptions")
	for device in bootList:
		if os.path.exists(device):
			if os.path.exists("/dev/block/by-name/flag"):
				Console().ePopen('mount --bind %s %s' % (device, tmp.dir))
			else:
				Console().ePopen('mount %s %s' % (device, tmp.dir))
			if os.path.isfile(os.path.join(tmp.dir, "STARTUP")):
				print('[Multiboot] Startupdevice found:', device)
				return device
			Console().ePopen('umount %s' % tmp.dir)
	if not os.path.ismount(tmp.dir):
		os.rmdir(tmp.dir)


def getparam(line, param):
	return line.replace("userdataroot", "rootuserdata").rsplit('%s=' % param, 1)[1].split(' ', 1)[0]


def getMultibootslots():
	bootslots = {}
	mode12found = False
	if SystemInfo["MultibootStartupDevice"]:
		for _file in glob.glob(os.path.join(tmp.dir, 'STARTUP_*')):
			if "STARTUP_RECOVERY" in _file:
				SystemInfo["RecoveryMode"] = True
				print("[multiboot] [getMultibootslots] RecoveryMode is set to:%s" % SystemInfo["RecoveryMode"])
			if 'MODE_' in _file:
				mode12found = True
				slotnumber = _file.rsplit('_', 3)[1]
			else:
				slotnumber = _file.rsplit('_', 1)[1]
			if slotnumber.isdigit() and slotnumber not in bootslots:
				slot = {}
				for line in open(_file).readlines():
					if 'root=' in line:
						device = getparam(line, 'root')
						if "UUID=" in device:
							slotx = str(getUUIDtoSD(device))
							if slotx is not None:
								device = slotx
						if os.path.exists(device) or device == 'ubi0:ubifs':
							slot['device'] = device
							slot['startupfile'] = os.path.basename(_file)
							if "sda" in line:
								slot["kernel"] = "/dev/sda%s" % line.split("sda", 1)[1].split(" ", 1)[0]
								slot["rootsubdir"] = None
							else:
								slot["kernel"] = "%sp%s" % (device.split("p")[0], int(device.split("p")[1]) - 1)
							if 'rootsubdir' in line:
								SystemInfo["HasRootSubdir"] = True
								slot['rootsubdir'] = getparam(line, 'rootsubdir')
								slot["kernel"] = getparam(line, "kernel")
						break
				if slot:
					bootslots[int(slotnumber)] = slot
		Console().ePopen('umount %s' % tmp.dir)
		if not os.path.ismount(tmp.dir):
			os.rmdir(tmp.dir)
		if not mode12found and SystemInfo["canMode12"]:
			#the boot device has ancient content and does not contain the correct STARTUP files
			for slot in range(1, 5):
				bootslots[slot] = {'device': '/dev/mmcblk0p%s' % (slot * 2 + 1), 'startupfile': None}
	print('[Multiboot] Bootslots found:', bootslots)
	return bootslots


def getCurrentImage():
	if SystemInfo["canMultiBoot"]:
		if SystemInfo["hasKexec"]:	# kexec kernel multiboot
			rootsubdir = [x for x in open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().split() if x.startswith("rootsubdir")]
			char = "/" if "/" in rootsubdir[0] else "="
			return int(rootsubdir[0].rsplit(char, 1)[1][11:])
		else: #legacy multiboot
			slot = [x[-1] for x in open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().split() if x.startswith('rootsubdir')]
			if slot:
				return int(slot[0])
			else:
				device = getparam(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read(), 'root')
				for slot in SystemInfo["canMultiBoot"].keys():
					if SystemInfo["canMultiBoot"][slot]['device'] == device:
						return slot


def getCurrentImageMode():
	return bool(SystemInfo["canMultiBoot"]) and SystemInfo["canMode12"] and int(open('/sys/firmware/devicetree/base/chosen/bootargs', 'r').read().replace('\0', '').split('=')[-1])


def deleteImage(slot):
	tmp.dir = tempfile.mkdtemp(prefix="Multiboot")
	Console().ePopen('mount %s %s' % (SystemInfo["canMultiBoot"][slot]['device'], tmp.dir))
	enigma2binaryfile = os.path.join(os.sep.join(filter(None, [tmp.dir, SystemInfo["canMultiBoot"][slot].get('rootsubdir', '')])), 'usr/bin/enigma2')
	if os.path.exists(enigma2binaryfile):
		os.rename(enigma2binaryfile, '%s.bak' % enigma2binaryfile)
	Console().ePopen('umount %s' % tmp.dir)
	if not os.path.ismount(tmp.dir):
		os.rmdir(tmp.dir)


def restoreImages():
	for slot in SystemInfo["canMultiBoot"]:
		tmp.dir = tempfile.mkdtemp(prefix="Multiboot")
		Console().ePopen('mount %s %s' % (SystemInfo["canMultiBoot"][slot]['device'], tmp.dir))
		enigma2binaryfile = os.path.join(os.sep.join(filter(None, [tmp.dir, SystemInfo["canMultiBoot"][slot].get('rootsubdir', '')])), 'usr/bin/enigma2')
		if os.path.exists('%s.bak' % enigma2binaryfile):
			os.rename('%s.bak' % enigma2binaryfile, enigma2binaryfile)
		Console().ePopen('umount %s' % tmp.dir)
		if not os.path.ismount(tmp.dir):
			os.rmdir(tmp.dir)

def getUUIDtoSD(UUID): # returns None on failure
	check = "/sbin/blkid"
	if fileExists(check):
		lines = subprocess.check_output([check]).decode(encoding="utf8", errors="ignore").split("\n")
		for line in lines:
			if UUID in line.replace('"', ''):
				return line.split(":")[0].strip()
	else:
		return None


def getImagelist():
	imagelist = {}
	if SystemInfo["canMultiBoot"]:
		tmp.dir = tempfile.mkdtemp(prefix="Multiboot")
		for slot in sorted(SystemInfo["canMultiBoot"].keys()):
			if SystemInfo["canMultiBoot"][slot]['device'] == 'ubi0:ubifs':
				Console().ePopen('mount -t ubifs %s %s' % (SystemInfo["canMultiBoot"][slot]['device'], tmp.dir))
			else:
				Console().ePopen('mount %s %s' % (SystemInfo["canMultiBoot"][slot]['device'], tmp.dir))
			imagedir = os.sep.join(filter(None, [tmp.dir, SystemInfo["canMultiBoot"][slot].get('rootsubdir', '')]))
			if os.path.isfile(os.path.join(imagedir, 'usr/bin/enigma2')):
				try:
					from datetime import datetime
					date = datetime.fromtimestamp(os.stat(os.path.join(imagedir, "var/lib/opkg/status")).st_mtime).strftime('%Y-%m-%d')
					if date.startswith("1970"):
						date = datetime.fromtimestamp(os.stat(os.path.join(imagedir, "usr/share/bootlogo.mvi")).st_mtime).strftime('%Y-%m-%d')
					date = max(date, datetime.fromtimestamp(os.stat(os.path.join(imagedir, "usr/bin/enigma2")).st_mtime).strftime('%Y-%m-%d'))
				except:
					date = _("Unknown")
				imagelist[slot] = {'imagename': "%s (%s)" % (open(os.path.join(imagedir, "etc/issue")).readlines()[-2].capitalize().strip()[:-6], date)}
				if os.path.exists(os.path.join(imagedir, "etc/image-version")):
					with open(os.path.join(imagedir, "etc/image-version"), 'r') as fp:
						lines = fp.readlines()
						for row in lines:
							word = 'imagetype'
							if row.find(word) != -1:
								imagetype=row.split('=')[1]
								imagelist[slot] = {'imagename': "%s - %s (%s)" % (open(os.path.join(imagedir, "etc/issue")).readlines()[-2].capitalize().strip()[:-6], imagetype.strip(), date)}
								break
			elif os.path.isfile(os.path.join(imagedir, 'usr/bin/enigma2.bak')):
				imagelist[slot] = {'imagename': _("Deleted image")}
			else:
				imagelist[slot] = {'imagename': _("Empty slot")}
			Console().ePopen('umount %s' % tmp.dir)
		if not os.path.ismount(tmp.dir):
			os.rmdir(tmp.dir)
	return imagelist
