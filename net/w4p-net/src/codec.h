// SPDX-License-Identifier: GPL-3.0-or-later
// w4p-net join/reply code codec (design: docs/research/m5_connection_design.md section 1.4).
//
// Binary record:
//   byte 0      (format version << 4) | kind        version 1; kind 1 = join code, 2 = reply code
//   byte 1      total record length L in bytes (including the CRC)
//   join:       session secret (10 bytes)
//   reply:      session tag (first 4 bytes of the 8-byte tag) + joiner nonce (5 bytes)
//   count       number of candidates (0..8)
//   candidate   (type << 4) | family (0 = IPv4, 1 = IPv6); address 4 or 16 bytes; port 2 bytes big-endian
//   CRC-16      CCITT-FALSE (poly 0x1021, init 0xFFFF) over bytes [0, L-2), big-endian
//
// Text: "W4P1-" + Crockford base32 of the record, a dash after every 5 symbols. The parser accepts lower case,
// reads I/L as 1 and O as 0, allows whitespace around the dashes, finds the code inside other pasted text and
// stops after the number of symbols given by the length byte. Group structure + length byte + CRC-16 together
// detect every single-character substitution, deletion and adjacent swap (test T1a, tests/codec_test.cpp).
#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <vector>

#include "siphash.h"

namespace w4p
{
	enum class CandType : uint8_t
	{
		Host = 0,
		Srflx = 1,
		Prflx = 2,
		Relay = 3,
	};

	struct Candidate
	{
		CandType type = CandType::Host;
		bool ipv6 = false;
		std::array<uint8_t, 16> addr{}; // network byte order; IPv4 uses the first 4 bytes
		uint16_t port = 0;

		bool operator==(const Candidate& o) const;
		bool operator!=(const Candidate& o) const { return !(*this == o); }
		std::string AddrString() const; // numeric address without port
		bool IsLoopback() const;
		bool IsPrivate() const; // RFC 1918 / CGNAT 100.64/10 / IPv6 ULA fc00::/7
		bool IsLinkLocal() const;
		std::string ClassName() const; // "loopback", "private", "link-local", "public" (for logs; never the IP)
		const char* TypeName() const;
		// Parses "a.b.c.d" or an IPv6 text address.
		static bool FromString(const std::string& ip, uint16_t port, CandType type, Candidate* out);
	};

	enum class CodeKind : uint8_t
	{
		Join = 1,
		Reply = 2,
	};

	constexpr int kFormatVersion = 1;
	constexpr size_t kNonceSize = 5;
	constexpr size_t kTagShortSize = 4;
	constexpr int kMaxCodeCandidates = 8;

	struct CodeRecord
	{
		CodeKind kind = CodeKind::Join;
		std::array<uint8_t, kSecretSize> secret{}; // join only
		std::array<uint8_t, kTagShortSize> tag{};  // reply only
		std::array<uint8_t, kNonceSize> nonce{};   // reply only
		std::vector<Candidate> cands;

		bool operator==(const CodeRecord& o) const;
	};

	enum class CodeError
	{
		None = 0,
		NotFound,   // no "W4P<digit>-" in the text
		Version,    // a code of another format version
		Incomplete, // text ends before the code is complete
		Mistyped,   // group structure, length or padding wrong
		Checksum,   // CRC-16 mismatch
		Format,     // record structure invalid
	};

	const char* CodeErrorMessage(CodeError e);

	uint16_t Crc16(const uint8_t* data, size_t len);

	std::vector<uint8_t> EncodeRecord(const CodeRecord& rec);
	CodeError DecodeRecord(const uint8_t* data, size_t len, CodeRecord* out);

	std::string FormatCode(const CodeRecord& rec);
	// Finds and decodes the first code in text. end_pos (optional) receives the offset after the code.
	CodeError ParseCode(const std::string& text, CodeRecord* out, size_t* end_pos = nullptr);

	// Candidate list blob used inside control messages: count byte + candidates as in the code.
	void AppendCandidates(std::vector<uint8_t>& out, const std::vector<Candidate>& cands);
	bool ReadCandidates(const uint8_t*& p, const uint8_t* end, std::vector<Candidate>* out);
} // namespace w4p
