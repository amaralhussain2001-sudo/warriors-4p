// SPDX-License-Identifier: GPL-3.0-or-later
#include "siphash.h"

#include <cstring>
#include <vector>

namespace w4p
{
	namespace
	{
		inline uint64_t Rotl(uint64_t x, int b) { return (x << b) | (x >> (64 - b)); }

		inline uint64_t Load64(const uint8_t* p)
		{
			uint64_t v = 0;
			for (int i = 7; i >= 0; i--)
				v = (v << 8) | p[i];
			return v;
		}

		inline void Round(uint64_t& v0, uint64_t& v1, uint64_t& v2, uint64_t& v3)
		{
			v0 += v1;
			v1 = Rotl(v1, 13);
			v1 ^= v0;
			v0 = Rotl(v0, 32);
			v2 += v3;
			v3 = Rotl(v3, 16);
			v3 ^= v2;
			v0 += v3;
			v3 = Rotl(v3, 21);
			v3 ^= v0;
			v2 += v1;
			v1 = Rotl(v1, 17);
			v1 ^= v2;
			v2 = Rotl(v2, 32);
		}
	} // namespace

	uint64_t SipHash24(const uint8_t key[16], const void* data, size_t len)
	{
		const uint8_t* in = static_cast<const uint8_t*>(data);
		const uint64_t k0 = Load64(key);
		const uint64_t k1 = Load64(key + 8);
		uint64_t v0 = 0x736f6d6570736575ULL ^ k0;
		uint64_t v1 = 0x646f72616e646f6dULL ^ k1;
		uint64_t v2 = 0x6c7967656e657261ULL ^ k0;
		uint64_t v3 = 0x7465646279746573ULL ^ k1;
		const size_t full = len & ~static_cast<size_t>(7);
		for (size_t i = 0; i < full; i += 8)
		{
			const uint64_t m = Load64(in + i);
			v3 ^= m;
			Round(v0, v1, v2, v3);
			Round(v0, v1, v2, v3);
			v0 ^= m;
		}
		uint64_t b = static_cast<uint64_t>(len) << 56;
		for (size_t i = 0; i < (len & 7); i++)
			b |= static_cast<uint64_t>(in[full + i]) << (8 * i);
		v3 ^= b;
		Round(v0, v1, v2, v3);
		Round(v0, v1, v2, v3);
		v0 ^= b;
		v2 ^= 0xff;
		for (int i = 0; i < 4; i++)
			Round(v0, v1, v2, v3);
		return v0 ^ v1 ^ v2 ^ v3;
	}

	uint64_t Prf(const uint8_t secret[kSecretSize], const char* label, const void* extra, size_t extra_len)
	{
		uint8_t key[16];
		std::memcpy(key, secret, kSecretSize);
		std::memcpy(key + kSecretSize, "W4P1KD", 6);
		std::vector<uint8_t> msg(label, label + std::strlen(label));
		msg.push_back(0);
		if (extra_len)
			msg.insert(msg.end(), static_cast<const uint8_t*>(extra), static_cast<const uint8_t*>(extra) + extra_len);
		return SipHash24(key, msg.data(), msg.size());
	}

	void DeriveKey16(const uint8_t secret[kSecretSize], const char* label, const void* extra, size_t extra_len,
		uint8_t out[16])
	{
		const std::string l1 = std::string(label) + "1";
		const std::string l2 = std::string(label) + "2";
		const uint64_t a = Prf(secret, l1.c_str(), extra, extra_len);
		const uint64_t b = Prf(secret, l2.c_str(), extra, extra_len);
		for (int i = 0; i < 8; i++)
		{
			out[i] = static_cast<uint8_t>(a >> (8 * i));
			out[8 + i] = static_cast<uint8_t>(b >> (8 * i));
		}
	}

	std::string Base32Plain(const void* data, size_t len)
	{
		static const char kAlpha[] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
		const uint8_t* p = static_cast<const uint8_t*>(data);
		std::string out;
		uint32_t acc = 0;
		int bits = 0;
		for (size_t i = 0; i < len; i++)
		{
			acc = (acc << 8) | p[i];
			bits += 8;
			while (bits >= 5)
			{
				out.push_back(kAlpha[(acc >> (bits - 5)) & 31]);
				bits -= 5;
			}
		}
		if (bits > 0)
			out.push_back(kAlpha[(acc << (5 - bits)) & 31]);
		return out;
	}
} // namespace w4p
