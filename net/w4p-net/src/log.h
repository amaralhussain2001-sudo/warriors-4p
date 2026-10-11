// SPDX-License-Identifier: GPL-3.0-or-later
// w4p-net logging: connection-log.txt (times relative to start), plain messages and "@" machine events on stdout.
// IP addresses are never written to the log; only their class (loopback/private/link-local/public) and port.
#pragma once

#include <cstdint>
#include <string>

namespace w4p
{
	int64_t NowUs(); // monotonic microseconds

	bool LogOpen(const std::string& path, int64_t t0_us);
	void LogClose();
	// Writes "[  12.345] text" to connection-log.txt.
	void Log(const char* fmt, ...);
	// Writes to the log and prints the text on stdout (what a player would see).
	void Say(const char* fmt, ...);
	// Prints "@<text>" on stdout (for the launcher / test harness) and writes it to the log.
	void Event(const char* fmt, ...);
	// Prints on stdout only (never in the log): used for codes, which contain the session secret and IP addresses.
	void Print(const char* fmt, ...);
} // namespace w4p
