// SPDX-License-Identifier: GPL-3.0-or-later
#include "codec.h"

#include <cstring>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#endif

namespace w4p
{
	namespace
	{
		const char kAlpha[] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
		const char kPrefix[] = "W4P";
		constexpr size_t kGroup = 5;

		// Crockford decoding: value 0..31, or -1 if not a symbol character.
		int SymbolValue(unsigned char c)
		{
			if (c >= '0' && c <= '9')
				return c - '0';
			if (c >= 'a' && c <= 'z')
				c = static_cast<unsigned char>(c - 'a' + 'A');
			switch (c)
			{
				case 'O': return 0;
				case 'I':
				case 'L': return 1;
				case 'U': return -1;
				default: break;
			}
			if (c < 'A' || c > 'Z')
				return -1;
			const char* p = std::strchr(kAlpha, c);
			return p ? static_cast<int>(p - kAlpha) : -1;
		}

		// Length in bytes of a whitespace character at text[pos] (ASCII space/tab/CR/LF, NBSP, zero-width space), else 0.
		size_t WhitespaceLen(const std::string& t, size_t pos)
		{
			if (pos >= t.size())
				return 0;
			const unsigned char c = static_cast<unsigned char>(t[pos]);
			if (c == ' ' || c == '\t' || c == '\r' || c == '\n')
				return 1;
			if (c == 0xC2 && pos + 1 < t.size() && static_cast<unsigned char>(t[pos + 1]) == 0xA0)
				return 2; // U+00A0
			if (c == 0xE2 && pos + 2 < t.size() && static_cast<unsigned char>(t[pos + 1]) == 0x80 &&
				static_cast<unsigned char>(t[pos + 2]) == 0x8B)
				return 3; // U+200B
			return 0;
		}

		// Length in bytes of a dash at text[pos] ('-', U+2010..U+2015, U+2212), else 0.
		size_t DashLen(const std::string& t, size_t pos)
		{
			if (pos >= t.size())
				return 0;
			const unsigned char c = static_cast<unsigned char>(t[pos]);
			if (c == '-')
				return 1;
			if (c == 0xE2 && pos + 2 < t.size())
			{
				const unsigned char c1 = static_cast<unsigned char>(t[pos + 1]);
				const unsigned char c2 = static_cast<unsigned char>(t[pos + 2]);
				if (c1 == 0x80 && c2 >= 0x90 && c2 <= 0x95)
					return 3;
				if (c1 == 0x88 && c2 == 0x92)
					return 3;
			}
			return 0;
		}

		size_t SkipWhitespace(const std::string& t, size_t pos)
		{
			size_t n;
			while ((n = WhitespaceLen(t, pos)) != 0)
				pos += n;
			return pos;
		}

		bool IsSymbolAt(const std::string& t, size_t pos)
		{
			return pos < t.size() && SymbolValue(static_cast<unsigned char>(t[pos])) >= 0;
		}

		size_t CandidateSize(bool ipv6) { return 1 + (ipv6 ? 16 : 4) + 2; }
	} // namespace

	bool Candidate::operator==(const Candidate& o) const
	{
		return type == o.type && ipv6 == o.ipv6 && port == o.port &&
			   std::memcmp(addr.data(), o.addr.data(), ipv6 ? 16 : 4) == 0;
	}

	std::string Candidate::AddrString() const
	{
		char buf[64] = {};
		if (ipv6)
			inet_ntop(AF_INET6, const_cast<uint8_t*>(addr.data()), buf, sizeof(buf));
		else
			inet_ntop(AF_INET, const_cast<uint8_t*>(addr.data()), buf, sizeof(buf));
		return buf;
	}

	bool Candidate::IsLoopback() const
	{
		if (!ipv6)
			return addr[0] == 127;
		static const uint8_t lo6[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1};
		return std::memcmp(addr.data(), lo6, 16) == 0;
	}

	bool Candidate::IsPrivate() const
	{
		if (!ipv6)
			return addr[0] == 10 || (addr[0] == 172 && (addr[1] & 0xF0) == 16) || (addr[0] == 192 && addr[1] == 168) ||
				   (addr[0] == 100 && (addr[1] & 0xC0) == 64);
		return (addr[0] & 0xFE) == 0xFC;
	}

	bool Candidate::IsLinkLocal() const
	{
		if (!ipv6)
			return addr[0] == 169 && addr[1] == 254;
		return addr[0] == 0xFE && (addr[1] & 0xC0) == 0x80;
	}

	std::string Candidate::ClassName() const
	{
		if (IsLoopback())
			return "loopback";
		if (IsLinkLocal())
			return "link-local";
		if (IsPrivate())
			return "private";
		return "public";
	}

	const char* Candidate::TypeName() const
	{
		switch (type)
		{
			case CandType::Host: return "host";
			case CandType::Srflx: return "srflx";
			case CandType::Prflx: return "prflx";
			case CandType::Relay: return "relay";
		}
		return "?";
	}

	bool Candidate::FromString(const std::string& ip, uint16_t port, CandType type, Candidate* out)
	{
		Candidate c;
		c.type = type;
		c.port = port;
		if (inet_pton(AF_INET, ip.c_str(), c.addr.data()) == 1)
			c.ipv6 = false;
		else if (inet_pton(AF_INET6, ip.c_str(), c.addr.data()) == 1)
			c.ipv6 = true;
		else
			return false;
		*out = c;
		return true;
	}

	bool CodeRecord::operator==(const CodeRecord& o) const
	{
		if (kind != o.kind || cands != o.cands)
			return false;
		if (kind == CodeKind::Join)
			return secret == o.secret;
		return tag == o.tag && nonce == o.nonce;
	}

	const char* CodeErrorMessage(CodeError e)
	{
		switch (e)
		{
			case CodeError::None: return "ok";
			case CodeError::NotFound: return "No code found. Copy the whole code (it starts with W4P1-).";
			case CodeError::Version: return "Your friend uses a different version of the co-op package.";
			case CodeError::Incomplete:
			case CodeError::Mistyped:
			case CodeError::Checksum:
			case CodeError::Format: return "This code is incomplete or mistyped. Copy it again.";
		}
		return "?";
	}

	uint16_t Crc16(const uint8_t* data, size_t len)
	{
		uint16_t crc = 0xFFFF;
		for (size_t i = 0; i < len; i++)
		{
			crc ^= static_cast<uint16_t>(data[i]) << 8;
			for (int b = 0; b < 8; b++)
				crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021) : static_cast<uint16_t>(crc << 1);
		}
		return crc;
	}

	void AppendCandidates(std::vector<uint8_t>& out, const std::vector<Candidate>& cands)
	{
		const size_t n = cands.size() > static_cast<size_t>(kMaxCodeCandidates) ? kMaxCodeCandidates : cands.size();
		out.push_back(static_cast<uint8_t>(n));
		for (size_t i = 0; i < n; i++)
		{
			const Candidate& c = cands[i];
			out.push_back(static_cast<uint8_t>((static_cast<uint8_t>(c.type) << 4) | (c.ipv6 ? 1 : 0)));
			out.insert(out.end(), c.addr.begin(), c.addr.begin() + (c.ipv6 ? 16 : 4));
			out.push_back(static_cast<uint8_t>(c.port >> 8));
			out.push_back(static_cast<uint8_t>(c.port & 0xFF));
		}
	}

	bool ReadCandidates(const uint8_t*& p, const uint8_t* end, std::vector<Candidate>* out)
	{
		if (p >= end)
			return false;
		const int n = *p++;
		if (n > kMaxCodeCandidates)
			return false;
		out->clear();
		for (int i = 0; i < n; i++)
		{
			if (p >= end)
				return false;
			const uint8_t tf = *p++;
			const int type = tf >> 4;
			const int fam = tf & 0x0F;
			if (type > 3 || fam > 1)
				return false;
			Candidate c;
			c.type = static_cast<CandType>(type);
			c.ipv6 = fam == 1;
			const size_t alen = c.ipv6 ? 16 : 4;
			if (static_cast<size_t>(end - p) < alen + 2)
				return false;
			std::memcpy(c.addr.data(), p, alen);
			p += alen;
			c.port = static_cast<uint16_t>((p[0] << 8) | p[1]);
			p += 2;
			out->push_back(c);
		}
		return true;
	}

	std::vector<uint8_t> EncodeRecord(const CodeRecord& rec)
	{
		std::vector<uint8_t> out;
		out.push_back(static_cast<uint8_t>((kFormatVersion << 4) | static_cast<uint8_t>(rec.kind)));
		out.push_back(0); // length, filled below
		if (rec.kind == CodeKind::Join)
			out.insert(out.end(), rec.secret.begin(), rec.secret.end());
		else
		{
			out.insert(out.end(), rec.tag.begin(), rec.tag.end());
			out.insert(out.end(), rec.nonce.begin(), rec.nonce.end());
		}
		AppendCandidates(out, rec.cands);
		out[1] = static_cast<uint8_t>(out.size() + 2);
		const uint16_t crc = Crc16(out.data(), out.size());
		out.push_back(static_cast<uint8_t>(crc >> 8));
		out.push_back(static_cast<uint8_t>(crc & 0xFF));
		return out;
	}

	CodeError DecodeRecord(const uint8_t* data, size_t len, CodeRecord* out)
	{
		if (len < 4)
			return CodeError::Format;
		if ((data[0] >> 4) != kFormatVersion)
			return CodeError::Version;
		if (data[1] != len)
			return CodeError::Mistyped;
		const uint16_t crc = static_cast<uint16_t>((data[len - 2] << 8) | data[len - 1]);
		if (Crc16(data, len - 2) != crc)
			return CodeError::Checksum;
		CodeRecord r;
		const int kind = data[0] & 0x0F;
		if (kind != 1 && kind != 2)
			return CodeError::Format;
		r.kind = static_cast<CodeKind>(kind);
		const uint8_t* p = data + 2;
		const uint8_t* end = data + len - 2;
		const size_t fixed = r.kind == CodeKind::Join ? kSecretSize : kTagShortSize + kNonceSize;
		if (static_cast<size_t>(end - p) < fixed)
			return CodeError::Format;
		if (r.kind == CodeKind::Join)
			std::memcpy(r.secret.data(), p, kSecretSize);
		else
		{
			std::memcpy(r.tag.data(), p, kTagShortSize);
			std::memcpy(r.nonce.data(), p + kTagShortSize, kNonceSize);
		}
		p += fixed;
		if (!ReadCandidates(p, end, &r.cands) || p != end)
			return CodeError::Format;
		*out = r;
		return CodeError::None;
	}

	std::string FormatCode(const CodeRecord& rec)
	{
		const std::vector<uint8_t> bytes = EncodeRecord(rec);
		const std::string sym = Base32Plain(bytes.data(), bytes.size());
		std::string out = std::string(kPrefix) + std::to_string(kFormatVersion) + "-";
		for (size_t i = 0; i < sym.size(); i++)
		{
			if (i && i % kGroup == 0)
				out.push_back('-');
			out.push_back(sym[i]);
		}
		return out;
	}

	CodeError ParseCode(const std::string& t, CodeRecord* out, size_t* end_pos)
	{
		// 1. Find "W4P<digit>-" (W and P in either case).
		size_t pos = std::string::npos;
		int version = -1;
		for (size_t i = 0; i + 5 <= t.size(); i++)
		{
			if ((t[i] == 'W' || t[i] == 'w') && t[i + 1] == '4' && (t[i + 2] == 'P' || t[i + 2] == 'p') &&
				t[i + 3] >= '0' && t[i + 3] <= '9' && DashLen(t, i + 4) > 0)
			{
				version = t[i + 3] - '0';
				pos = i + 4 + DashLen(t, i + 4);
				break;
			}
		}
		if (pos == std::string::npos)
			return CodeError::NotFound;
		if (version != kFormatVersion)
			return CodeError::Version;
		pos = SkipWhitespace(t, pos);

		// 2. Read symbols in groups of 5 separated by a dash (whitespace allowed around the dash) until the number of
		//    symbols given by the length byte (in symbols 0..3) is reached.
		std::vector<uint8_t> sym;
		size_t glen = 0;
		size_t need = 0; // total symbols, known after 4 symbols
		while (need == 0 || sym.size() < need)
		{
			if (IsSymbolAt(t, pos))
			{
				if (glen == kGroup)
					return CodeError::Mistyped; // group too long (a dash is missing)
				sym.push_back(static_cast<uint8_t>(SymbolValue(static_cast<unsigned char>(t[pos]))));
				pos++;
				glen++;
				if (sym.size() == 4)
				{
					const uint32_t bits = (sym[0] << 15) | (sym[1] << 10) | (sym[2] << 5) | sym[3];
					const uint32_t L = (bits >> 4) & 0xFF; // byte 1 = bits 8..15 of the stream
					if (L < 14)
						return CodeError::Mistyped;
					need = (8 * L + 4) / 5;
				}
				continue;
			}
			// separator: whitespace* dash whitespace*
			size_t q = SkipWhitespace(t, pos);
			const size_t d = DashLen(t, q);
			if (d == 0)
				break; // end of the code text
			if (glen != kGroup)
				return CodeError::Mistyped; // a symbol is missing in this group, or a stray dash
			pos = SkipWhitespace(t, q + d);
			glen = 0;
		}
		if (need == 0 || sym.size() < need)
			return CodeError::Incomplete;
		// 3. The code must end here: no symbol or "-symbol" directly after it.
		if (IsSymbolAt(t, pos))
			return CodeError::Mistyped;
		if (const size_t d = DashLen(t, pos); d && IsSymbolAt(t, pos + d))
			return CodeError::Mistyped;
		if (end_pos)
			*end_pos = pos;

		// 4. Symbols to bytes; padding bits must be zero.
		const size_t L = (((sym[0] << 15) | (sym[1] << 10) | (sym[2] << 5) | sym[3]) >> 4) & 0xFF;
		std::vector<uint8_t> bytes;
		bytes.reserve(L);
		uint32_t acc = 0;
		int nbits = 0;
		for (uint8_t s : sym)
		{
			acc = (acc << 5) | s;
			nbits += 5;
			if (nbits >= 8)
			{
				bytes.push_back(static_cast<uint8_t>(acc >> (nbits - 8)));
				nbits -= 8;
				acc &= (1u << nbits) - 1;
			}
		}
		if (bytes.size() != L || acc != 0)
			return CodeError::Mistyped;
		return DecodeRecord(bytes.data(), bytes.size(), out);
	}
} // namespace w4p
