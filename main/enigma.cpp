#include <unistd.h>
#include <iostream>
#include <fstream>
#include <vector>
#include <fcntl.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <libsig_comp.h>
#include <linux/dvb/version.h>
#include <lib/actions/action.h>
#include <lib/driver/rc.h>
#include <lib/base/ioprio.h>
#include <lib/base/e2avahi.h>
#include <lib/base/ebase.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/gmaindc.h>
#include <lib/gdi/glcddc.h>
#include <lib/gdi/grc.h>
#include <lib/gdi/epng.h>
#include <lib/gdi/font.h>
#include <lib/gui/ebutton.h>
#include <lib/gui/elabel.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/evideo.h>
#include <lib/python/connections.h>
#include <lib/python/python.h>
#include <lib/python/pythonconfig.h>
#include <lib/service/servicepeer.h>

#include "bsod.h"
#include "version_info.h"

#include <gst/gst.h>

#include <unistd.h>
#include <lib/components/scan.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/dvbtime.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/epgtransponderdatareader.h>
#include <malloc.h>

#ifdef OBJECT_DEBUG
int object_total_remaining;

void object_dump()
{
	printf("%d items left\n", object_total_remaining);
}
#endif

static eWidgetDesktop *wdsk, *lcddsk;
static int prev_ascii_code;

void setPrevAsciiCode(int code)
{
	prev_ascii_code = code;
}

int getPrevAsciiCode()
{
	int ret = prev_ascii_code;
	prev_ascii_code = 0;
	return ret;
}

void keyEvent(const eRCKey &key)
{
	static eRCKey last(0, 0, 0);
	static int num_repeat;

	ePtr<eActionMap> ptr;
	eActionMap::getInstance(ptr);
	/*eDebug("key.code : %02x \n", key.code);*/

	if ((key.code == last.code) && (key.producer == last.producer) && key.flags & eRCKey::flagRepeat)
		num_repeat++;
	else
	{
		num_repeat = 0;
		last = key;
	}

	if (num_repeat == 4)
	{
		ptr->keyPressed(key.producer->getIdentifier(), key.code, eRCKey::flagLong);
		num_repeat++;
	}

	if (key.flags & eRCKey::flagAscii)
	{
		prev_ascii_code = key.code;
		ptr->keyPressed(key.producer->getIdentifier(), 510 /* faked KEY_ASCII */, 0);
	}
	else
		ptr->keyPressed(key.producer->getIdentifier(), key.code, key.flags);
}

/************************************************/

/* Defined in eerror.cpp */
void setDebugTime(bool enable);
class eMain: public eApplication, public sigc::trackable
{
	eInit init;
	ePythonConfigQuery config;

	ePtr<eDVBDB> m_dvbdb;
	ePtr<eDVBResourceManager> m_mgr;
	ePtr<eDVBLocalTimeHandler> m_locale_time_handler;
	ePtr<eEPGCache> m_epgcache;
	ePtr<eEPGTransponderDataReader> m_epgtransponderdatareader;

public:
	eMain()
	{
		e2avahi_init(this);
		init_servicepeer();
		init.setRunlevel(eAutoInitNumbers::main);
		/* TODO: put into init */
		m_dvbdb = new eDVBDB();
		m_mgr = new eDVBResourceManager();
		m_locale_time_handler = new eDVBLocalTimeHandler();
		m_epgcache = new eEPGCache();
		m_epgtransponderdatareader = new eEPGTransponderDataReader();
		m_mgr->setChannelList(m_dvbdb);
	}

	~eMain()
	{
		m_dvbdb->saveServicelist();
		m_mgr->releaseCachedChannel();
		done_servicepeer();
		e2avahi_close();
	}
};

bool fileExists(const std::string& path) {
	std::ifstream file(path.c_str());
	return file.good();
}

bool getConfigBoolValue(const std::string& configFile, const std::string& key, bool defaultValue) {
	std::ifstream in(configFile);
	if (!in.is_open()) {
		eDebug("[MAIN] Error opening config file: %s", configFile.c_str());
		return defaultValue;
	}

	std::string line;
	while (std::getline(in, line)) {
		if (line.find(key) != std::string::npos) {
			size_t pos = line.find('=');
			if (pos != std::string::npos) {
				std::string valueStr = line.substr(pos + 1);
				// Trim leading and trailing whitespace
				size_t start = valueStr.find_first_not_of(" \t");
				size_t end = valueStr.find_last_not_of(" \t");
				if (start != std::string::npos && end != std::string::npos) {
					valueStr = valueStr.substr(start, end - start + 1);
				}
				// Check if valueStr is "true" or "false"
				if (valueStr == "true" || valueStr == "TRUE") {
					return true;
				} else if (valueStr == "false" || valueStr == "FALSE") {
					return false;
				} else {
					break;
				}
			}
		}
	}

	return defaultValue;
}

static const std::string getConfigCurrentSpinner(const std::string &key) {
	std::string value;
	std::ifstream in(eEnv::resolve("${sysconfdir}/enigma2/settings").c_str());

	if (in.good()) {
		std::string line;
		while (std::getline(in, line)) {
			if (line.compare(0, key.size(), key) == 0) {
				value = line.substr(key.size() + 1);
				size_t end_pos = value.find("skin.xml");
				if (end_pos != std::string::npos) {
					value = value.substr(0, end_pos);
				}
				break;
			}
		}
		in.close();
	}

	if (value.empty()) {
		value = "GigabluePaxV2";
	}

	std::vector<std::string> directories;
	bool useDefaultSpinner = getConfigBoolValue("/etc/enigma2/settings", "config.usage.usedefaultspinner", false);

	if (!useDefaultSpinner) {
		directories.push_back("/usr/share/enigma2/" + value + "/spinner/wait1.png");
		directories.push_back("/usr/share/enigma2/" + value + "/skin_default/spinner/wait1.png");
	}
	directories.push_back("/usr/share/enigma2/skin_default/spinner/wait1.png");

	for (const auto& dir : directories) {

		if (fileExists(dir)) {
			if (dir.find("skin_default") != std::string::npos && dir.find(value) != std::string::npos) {
				return value + "/skin_default";
			} else if (dir.find("skin_default") != std::string::npos) {
				return "skin_default";
			} else {
				return value;
			}
		}
	}

	return "skin_default";
}


int exit_code;

void quitMainloop(int exitCode)
{
	FILE *f = fopen("/proc/stb/fp/was_timer_wakeup", "w");
	if (f) {
		fprintf(f, "%d", 0);
		fclose(f);
	} else {
		int fd = open("/dev/dbox/fp0", O_WRONLY);
		if (fd >= 0) {
			if (ioctl(fd, 10 /*FP_CLEAR_WAKEUP_TIMER*/) < 0)
				eDebug("[quitMainloop] FP_CLEAR_WAKEUP_TIMER failed: %m");
			close(fd);
		} else {
			eDebug("[quitMainloop] open /dev/dbox/fp0 for wakeup timer clear failed: %m");
		}
	}
	exit_code = exitCode;
	eApp->quit(0);
}

void pauseInit()
{
	eInit::pauseInit();
}

void resumeInit()
{
	eInit::resumeInit();
}

static void sigterm_handler(int num)
{
	quitMainloop(128 + num);
}

void catchTermSignal()
{
	struct sigaction act = {};

	act.sa_handler = sigterm_handler;
	act.sa_flags = SA_RESTART;

	if (sigemptyset(&act.sa_mask) == -1)
		perror("sigemptyset");
	if (sigaction(SIGTERM, &act, 0) == -1)
		perror("SIGTERM");
}

int main(int argc, char **argv)
{
#ifdef MEMLEAK_CHECK
	atexit(DumpUnfreed);
#endif

#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif

	gst_init(&argc, &argv);

	setenv("PYTHONPATH", eEnv::resolve("${libdir}/enigma2/python").c_str(), 0);
	printf("[enigma2] PYTHONPATH: %s\n", getenv("PYTHONPATH"));
	printf("[enigma2] DVB_API_VERSION %d DVB_API_VERSION_MINOR %d\n", DVB_API_VERSION, DVB_API_VERSION_MINOR);

	debugLvl = getenv("ENIGMA_DEBUG_LVL") ? atoi(getenv("ENIGMA_DEBUG_LVL")) : DEFAULT_DEBUG_LVL;
	if (debugLvl < 0)
		debugLvl = 0;
	printf("ENIGMA_DEBUG_LVL=%d\n", debugLvl);
	if (getenv("ENIGMA_DEBUG_TIME"))
		setDebugTime(atoi(getenv("ENIGMA_DEBUG_TIME")) != 0);

	ePython python;
	eMain main;

	ePtr<gMainDC> my_dc;
	gMainDC::getInstance(my_dc);

	ePtr<gLCDDC> my_lcd_dc;
	gLCDDC::getInstance(my_lcd_dc);

	for (int i = 0x60c; i <= 0x66d; ++i)
		eTextPara::forceReplacementGlyph(i);
	eTextPara::forceReplacementGlyph(0xfdf2);
	for (int i = 0xfe80; i < 0xff00; ++i)
		eTextPara::forceReplacementGlyph(i);

	eWidgetDesktop dsk(my_dc->size());
	eWidgetDesktop dsk_lcd(my_lcd_dc->size());

	dsk.setStyleID(0);
	dsk_lcd.setStyleID(1);

	wdsk = &dsk;
	lcddsk = &dsk_lcd;

	dsk.setDC(my_dc);
	dsk_lcd.setDC(my_lcd_dc);

	dsk.setBackgroundColor(gRGB(0,0,0,0xFF));

	dsk.setRedrawTask(main);
	dsk_lcd.setRedrawTask(main);

	std::string active_skin = getConfigCurrentSpinner("config.skin.primary_skin");
	eDebug("[MAIN] Loading spinners from /usr/share/enigma2/%s/spinner/", active_skin.c_str());

	int i;
	#define MAX_SPINNER 64
	ePtr<gPixmap> wait[MAX_SPINNER];
	for (i=0; i<MAX_SPINNER; ++i)
	{
		char filename[64] = {};
		std::string rfilename;
		snprintf(filename, sizeof(filename), "${datadir}/enigma2/%s/spinner/wait%d.png", active_skin.c_str(), i + 1);
		rfilename = eEnv::resolve(filename);

		if (::access(rfilename.c_str(), R_OK) < 0)
			break;

		loadImage(wait[i], rfilename.c_str());
		if (!wait[i])
		{
			eDebug("[MAIN] failed to load %s: %m", rfilename.c_str());
			break;
		}
	}
	eDebug("[MAIN] found %d spinner!", i);
	if (i)
		my_dc->setSpinner(eRect(ePoint(25, 25), wait[0]->size()), wait, i);
	else
		my_dc->setSpinner(eRect(25, 25, 0, 0), wait, 1);

	gRC::getInstance()->setSpinnerDC(my_dc);

	eRCInput::getInstance()->keyEvent.connect(sigc::ptr_fun(&keyEvent));

	printf("[MAIN] executing main\n");

	bsodCatchSignals();
	catchTermSignal();

	setIoPrio(IOPRIO_CLASS_BE, 3);

	eVideoWidget::setFullsize(true);

	python.execFile(eEnv::resolve("${libdir}/enigma2/python/StartEnigma.py").c_str());

	eVideoWidget::setFullsize(true);

	if (exit_code == 5) /* python crash */
	{
		eDebug("[MAIN] (exit code 5)");
		bsodFatal(0);
	}

	dsk.paint();
	dsk_lcd.paint();

	{
		gPainter p(my_lcd_dc);
		p.resetClip(eRect(ePoint(0, 0), my_lcd_dc->size()));
		p.clear();
		p.flush();
	}

	return exit_code;
}

eWidgetDesktop *getDesktop(int which)
{
	return which ? lcddsk : wdsk;
}

eApplication *getApplication()
{
	return eApp;
}

void runMainloop()
{
	catchTermSignal();
	eApp->runLoop();
}

const char *getEnigmaVersionString()
{
	return enigma2_date;
}

const char *getE2Rev()
{
	return E2REV;
}

const char *getGStreamerVersionString()
{
	return gst_version_string();
}

void dump_malloc_stats(void)
{
#ifdef __GLIBC__
#if __GLIBC__ > 2 || (__GLIBC__ == 2 && __GLIBC_MINOR__ >= 33)
	struct mallinfo2 mi = mallinfo2();
	eDebug("MALLOC: %zu total", mi.uordblks);
#else
	struct mallinfo mi = mallinfo();
	eDebug("MALLOC: %d total", mi.uordblks);
#endif
#else
	eDebug("MALLOC: info not exposed");
#endif
}
