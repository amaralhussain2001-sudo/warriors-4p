// SPDX-License-Identifier: GPL-3.0-or-later
// w4p-net: connection helper for warriors-4p (4-player online co-op on the patched PCSX2 fork).
// Usage: see README.md or run "w4p-net --help".
#include "helper.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

namespace
{
	void Usage()
	{
		std::puts(
			"w4p-net host [options]            host a game; prints a join code\n"
			"w4p-net join <text with code> [options]\n"
			"                                  join a game; prints a reply code (send it only if not connected in 10 s)\n"
			"While running, type or pipe lines on stdin: a reply code (host), 'status', 'probe RATE SIZE SECONDS',\n"
			"'lock' (host: no new players), 'quit'. Closing stdin also quits.\n"
			"\n"
			"Options:\n"
			"  --players N           host: number of players 2..4 (default 4)\n"
			"  --ice-port P          UDP port for the internet connection (default 41500; tries P..P+19)\n"
			"  --bind ADDR           bind the ICE socket to ADDR (default: all interfaces; tests: 127.0.0.1)\n"
			"  --stun HOST:PORT      STUN server (default stun.cloudflare.com:3478)\n"
			"  --no-stun             do not contact any STUN server (host candidates only)\n"
			"  --emu-port P          emulator W4P ListenPort on 127.0.0.1 (default 41000)\n"
			"  --slot-ports B        helper loopback ports B..B+3; W4P Peer<p> = 127.0.0.1:B+p (default 41100)\n"
			"  --want-slot N         joiner: ask for slot N (1..3)\n"
			"  --log FILE            connection log (default connection-log.txt)\n"
			"  --stats FILE          write final statistics as JSON\n"
			"  --max-seconds S       exit after S seconds\n"
			"  --connect-minutes M   keep retrying a connection for M minutes (default 10)\n"
			"  --no-stdin            do not read commands from stdin\n"
			"  --verbose             libjuice debug messages in the log\n"
			"Test switches (single-PC tests only):\n"
			"  --test-no-direct-dial host ignores direct dial-in (forces the reply-code path)\n"
			"  --test-block-peer N   joiner: no direct link to slot N (traffic goes through the host); give it on both sides");
	}

	bool HostPort(const std::string& s, std::string* host, int* port)
	{
		const size_t c = s.rfind(':');
		if (c == std::string::npos)
			return false;
		*host = s.substr(0, c);
		*port = std::atoi(s.c_str() + c + 1);
		return !host->empty() && *port > 0 && *port < 65536;
	}
} // namespace

int main(int argc, char** argv)
{
	w4p::Options o;
	if (argc < 2 || !std::strcmp(argv[1], "--help") || !std::strcmp(argv[1], "-h"))
	{
		Usage();
		return argc < 2 ? 1 : 0;
	}
	int i = 1;
	const std::string mode = argv[i++];
	if (mode == "host")
		o.host = true;
	else if (mode == "join")
	{
		// Everything up to the first option is the pasted text (the code may contain spaces or line breaks).
		while (i < argc && std::strncmp(argv[i], "--", 2) != 0)
		{
			if (!o.join_text.empty())
				o.join_text += " ";
			o.join_text += argv[i++];
		}
		if (o.join_text.empty())
		{
			std::fputs("join: give the join code\n", stderr);
			return 1;
		}
	}
	else
	{
		Usage();
		return 1;
	}
	for (; i < argc; i++)
	{
		const std::string a = argv[i];
		auto next = [&](const char* name) -> const char* {
			if (i + 1 >= argc)
			{
				std::fprintf(stderr, "%s needs a value\n", name);
				std::exit(1);
			}
			return argv[++i];
		};
		if (a == "--players")
			o.players = std::atoi(next("--players"));
		else if (a == "--ice-port")
			o.ice_port = std::atoi(next("--ice-port"));
		else if (a == "--bind")
			o.bind_addr = next("--bind");
		else if (a == "--stun")
		{
			if (!HostPort(next("--stun"), &o.stun_host, &o.stun_port))
			{
				std::fputs("--stun needs HOST:PORT\n", stderr);
				return 1;
			}
			o.stun = true;
		}
		else if (a == "--no-stun")
			o.stun = false;
		else if (a == "--emu-port")
			o.emu_port = std::atoi(next("--emu-port"));
		else if (a == "--slot-ports")
			o.slot_port_base = std::atoi(next("--slot-ports"));
		else if (a == "--want-slot")
			o.want_slot = std::atoi(next("--want-slot"));
		else if (a == "--log")
			o.log_path = next("--log");
		else if (a == "--stats")
			o.stats_path = next("--stats");
		else if (a == "--max-seconds")
			o.max_seconds = std::atof(next("--max-seconds"));
		else if (a == "--connect-minutes")
			o.connect_minutes = std::atoi(next("--connect-minutes"));
		else if (a == "--no-stdin")
			o.read_stdin = false;
		else if (a == "--verbose")
			o.verbose = true;
		else if (a == "--test-no-direct-dial")
			o.test_no_direct_dial = true;
		else if (a == "--test-block-peer")
			o.test_block_peers.push_back(std::atoi(next("--test-block-peer")));
		else
		{
			std::fprintf(stderr, "unknown option %s\n", a.c_str());
			return 1;
		}
	}
	w4p::Helper h(o);
	return h.Run();
}
