// SPDX-License-Identifier: GPL-3.0-or-later
// Test T1a (docs/research/m5_connection_design.md section 6): code codec round trip with 10,000 random descriptions,
// and every single-character substitution, deletion and adjacent swap of each code must be detected (or decode to
// exactly the same description, e.g. lower case or the I/L/O aliases, which is harmless).
// Also checks the SipHash-2-4 and CRC-16 implementations against published test values.
// Usage: w4p-net-codec-test [count] [seed]   (defaults 10000, 20261011). Exit code 0 = pass.
#include "codec.h"
#include "siphash.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>

#ifdef _WIN32
#include <winsock2.h>
#endif

using namespace w4p;

namespace
{
	int g_fail = 0;

	void Check(bool ok, const char* what)
	{
		std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
		if (!ok)
			g_fail++;
	}

	CodeRecord RandomRecord(std::mt19937_64& rng)
	{
		CodeRecord r;
		r.kind = (rng() & 1) ? CodeKind::Join : CodeKind::Reply;
		for (auto& b : r.secret)
			b = static_cast<uint8_t>(rng());
		if (r.kind == CodeKind::Reply)
		{
			r.secret = {};
			for (auto& b : r.tag)
				b = static_cast<uint8_t>(rng());
			for (auto& b : r.nonce)
				b = static_cast<uint8_t>(rng());
		}
		const int n = static_cast<int>(rng() % 7); // 0..6 candidates
		for (int i = 0; i < n; i++)
		{
			Candidate c;
			c.type = static_cast<CandType>(rng() % 4);
			c.ipv6 = (rng() % 4) == 0;
			for (int k = 0; k < (c.ipv6 ? 16 : 4); k++)
				c.addr[k] = static_cast<uint8_t>(rng());
			c.port = static_cast<uint16_t>(rng());
			r.cands.push_back(c);
		}
		return r;
	}

	struct Tally
	{
		long long tried = 0, detected = 0, same = 0, undetected = 0;
	};

	void Classify(const std::string& text, const CodeRecord& orig, Tally& t, std::string* example)
	{
		t.tried++;
		CodeRecord got;
		const CodeError e = ParseCode(text, &got);
		if (e != CodeError::None)
			t.detected++;
		else if (got == orig)
			t.same++;
		else
		{
			t.undetected++;
			if (example && example->empty())
				*example = text;
		}
	}
} // namespace

int main(int argc, char** argv)
{
#ifdef _WIN32
	WSADATA wsa;
	WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
	const int count = argc > 1 ? std::atoi(argv[1]) : 10000;
	const unsigned long long seed = argc > 2 ? std::strtoull(argv[2], nullptr, 10) : 20261011ULL;
	const auto t0 = std::chrono::steady_clock::now();

	// SipHash-2-4 test values from the SipHash paper / reference vectors (key 00..0f).
	{
		uint8_t key[16], msg[15];
		for (int i = 0; i < 16; i++)
			key[i] = static_cast<uint8_t>(i);
		for (int i = 0; i < 15; i++)
			msg[i] = static_cast<uint8_t>(i);
		Check(SipHash24(key, msg, 0) == 0x726fdb47dd0e0e31ULL, "SipHash-2-4 empty message = 726fdb47dd0e0e31");
		Check(SipHash24(key, msg, 15) == 0xa129ca6149be45e5ULL, "SipHash-2-4 15-byte message = a129ca6149be45e5");
	}
	// CRC-16/CCITT-FALSE check value.
	Check(Crc16(reinterpret_cast<const uint8_t*>("123456789"), 9) == 0x29B1, "CRC-16/CCITT-FALSE(\"123456789\") = 29B1");

	// Characters used for substitutions: all Crockford symbols, lower case, the excluded letters, dash, space, others.
	const std::string subs = "0123456789ABCDEFGHJKMNPQRSTVWXYZabcdefghijklmnopqrstuvwxyzILOU- _.";

	std::mt19937_64 rng(seed);
	long long rt_ok = 0, rt_embedded_ok = 0, rt_lower_ok = 0, rt_wrapped_ok = 0;
	Tally sub, del, swp;
	std::string ex_sub, ex_del, ex_swp;
	size_t min_len = 1 << 30, max_len = 0;
	double sum_len = 0;
	for (int n = 0; n < count; n++)
	{
		const CodeRecord rec = RandomRecord(rng);
		const std::string code = FormatCode(rec);
		min_len = code.size() < min_len ? code.size() : min_len;
		max_len = code.size() > max_len ? code.size() : max_len;
		sum_len += static_cast<double>(code.size());
		CodeRecord got;
		if (ParseCode(code, &got) == CodeError::None && got == rec)
			rt_ok++;
		if (ParseCode("Hey, join my game: " + code + " - see you!\r\n", &got) == CodeError::None && got == rec)
			rt_embedded_ok++;
		std::string lower = code;
		for (char& c : lower)
			if (c >= 'A' && c <= 'Z')
				c = static_cast<char>(c - 'A' + 'a');
		if (ParseCode(lower, &got) == CodeError::None && got == rec)
			rt_lower_ok++;
		// line break after a dash (what a hard-wrapping chat could do)
		std::string wrapped = code;
		const size_t dash = wrapped.find('-', 10 + (rng() % 20));
		if (dash != std::string::npos)
			wrapped.insert(dash + 1, "\r\n");
		if (ParseCode(wrapped, &got) == CodeError::None && got == rec)
			rt_wrapped_ok++;

		for (size_t i = 0; i < code.size(); i++)
		{
			for (char c : subs)
			{
				if (c == code[i])
					continue;
				std::string m = code;
				m[i] = c;
				Classify(m, rec, sub, &ex_sub);
			}
			std::string d = code;
			d.erase(i, 1);
			Classify(d, rec, del, &ex_del);
			if (i + 1 < code.size() && code[i] != code[i + 1])
			{
				std::string s = code;
				std::swap(s[i], s[i + 1]);
				Classify(s, rec, swp, &ex_swp);
			}
		}
	}
	const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();

	std::printf("descriptions: %d (seed %llu), code length min %zu / avg %.1f / max %zu characters\n", count, seed,
		min_len, sum_len / count, max_len);
	std::printf("round trip: %lld/%d plain, %lld/%d inside other text, %lld/%d lower case, %lld/%d line break after a dash\n",
		rt_ok, count, rt_embedded_ok, count, rt_lower_ok, count, rt_wrapped_ok, count);
	std::printf("substitutions: tried %lld, detected %lld, same description %lld, UNDETECTED %lld\n", sub.tried,
		sub.detected, sub.same, sub.undetected);
	std::printf("deletions:     tried %lld, detected %lld, same description %lld, UNDETECTED %lld\n", del.tried,
		del.detected, del.same, del.undetected);
	std::printf("swaps:         tried %lld, detected %lld, same description %lld, UNDETECTED %lld\n", swp.tried,
		swp.detected, swp.same, swp.undetected);
	if (!ex_sub.empty())
		std::printf("example undetected substitution: %s\n", ex_sub.c_str());
	if (!ex_del.empty())
		std::printf("example undetected deletion: %s\n", ex_del.c_str());
	if (!ex_swp.empty())
		std::printf("example undetected swap: %s\n", ex_swp.c_str());
	Check(rt_ok == count && rt_embedded_ok == count && rt_lower_ok == count && rt_wrapped_ok == count,
		"round trip of every description (plain, embedded, lower case, wrapped)");
	Check(sub.undetected == 0, "every single-character substitution detected or harmless");
	Check(del.undetected == 0, "every single-character deletion detected or harmless");
	Check(swp.undetected == 0, "every adjacent swap detected or harmless");

	// Example sizes for the design table (1 LAN IPv4 host + 1 public IPv4 srflx; + IPv6 host).
	{
		CodeRecord j;
		j.kind = CodeKind::Join;
		Candidate a, b, c;
		Candidate::FromString("192.168.1.20", 41500, CandType::Host, &a);
		Candidate::FromString("203.0.113.7", 41500, CandType::Srflx, &b);
		Candidate::FromString("2001:db8::1234:5678:9abc:def0", 41500, CandType::Host, &c);
		j.cands = {a, b};
		CodeRecord r = j;
		r.kind = CodeKind::Reply;
		std::printf("size: join code, 1 LAN + 1 public IPv4: %zu bytes, %zu characters\n", EncodeRecord(j).size(),
			FormatCode(j).size());
		std::printf("size: reply code, 1 LAN + 1 public IPv4: %zu bytes, %zu characters\n", EncodeRecord(r).size(),
			FormatCode(r).size());
		j.cands.push_back(c);
		std::printf("size: join code, + 1 IPv6: %zu bytes, %zu characters\n", EncodeRecord(j).size(), FormatCode(j).size());
		std::printf("example join code (documentation addresses): %s\n", FormatCode(j).c_str());
	}
	std::printf("time: %.1f s\n", secs);
	std::printf("RESULT %s (%d failed checks)\n", g_fail ? "FAIL" : "PASS", g_fail);
	return g_fail ? 1 : 0;
}
