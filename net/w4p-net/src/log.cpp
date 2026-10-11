// SPDX-License-Identifier: GPL-3.0-or-later
#include "log.h"

#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <mutex>
#include <vector>

namespace w4p
{
	namespace
	{
		std::mutex g_mx;
		FILE* g_file = nullptr;
		int64_t g_t0 = 0;

		std::string Format(const char* fmt, va_list ap)
		{
			va_list ap2;
			va_copy(ap2, ap);
			const int n = std::vsnprintf(nullptr, 0, fmt, ap2);
			va_end(ap2);
			if (n <= 0)
				return std::string();
			std::vector<char> buf(static_cast<size_t>(n) + 1);
			std::vsnprintf(buf.data(), buf.size(), fmt, ap);
			return std::string(buf.data(), static_cast<size_t>(n));
		}

		void Write(const char* prefix, bool to_log, bool to_stdout, const char* fmt, va_list ap)
		{
			const std::string text = Format(fmt, ap);
			std::lock_guard<std::mutex> lock(g_mx);
			if (to_log && g_file)
			{
				const double t = static_cast<double>(NowUs() - g_t0) / 1e6;
				std::fprintf(g_file, "[%9.3f] %s%s\n", t, prefix ? prefix : "", text.c_str());
				std::fflush(g_file);
			}
			if (to_stdout)
			{
				std::fputs(prefix ? prefix : "", stdout);
				std::fputs(text.c_str(), stdout);
				std::fputc('\n', stdout);
				std::fflush(stdout);
			}
		}
	} // namespace

	int64_t NowUs()
	{
		return std::chrono::duration_cast<std::chrono::microseconds>(
			std::chrono::steady_clock::now().time_since_epoch())
			.count();
	}

	bool LogOpen(const std::string& path, int64_t t0_us)
	{
		std::lock_guard<std::mutex> lock(g_mx);
		g_t0 = t0_us;
		g_file = std::fopen(path.c_str(), "w");
		return g_file != nullptr;
	}

	void LogClose()
	{
		std::lock_guard<std::mutex> lock(g_mx);
		if (g_file)
			std::fclose(g_file);
		g_file = nullptr;
	}

	void Log(const char* fmt, ...)
	{
		va_list ap;
		va_start(ap, fmt);
		Write(nullptr, true, false, fmt, ap);
		va_end(ap);
	}

	void Say(const char* fmt, ...)
	{
		va_list ap;
		va_start(ap, fmt);
		Write(nullptr, true, true, fmt, ap);
		va_end(ap);
	}

	void Event(const char* fmt, ...)
	{
		va_list ap;
		va_start(ap, fmt);
		Write("@", true, true, fmt, ap);
		va_end(ap);
	}

	void Print(const char* fmt, ...)
	{
		va_list ap;
		va_start(ap, fmt);
		Write(nullptr, false, true, fmt, ap);
		va_end(ap);
	}
} // namespace w4p
