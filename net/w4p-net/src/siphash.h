// SPDX-License-Identifier: GPL-3.0-or-later
// w4p-net: SipHash-2-4 (Aumasson/Bernstein) used as a MAC and as a pseudorandom function (PRF).
// Own implementation written from the algorithm description; checked against the published test vectors
// (key 00..0f; empty message and 15-byte message 00..0e) in tests/codec_test.cpp.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>

namespace w4p
{
	uint64_t SipHash24(const uint8_t key[16], const void* data, size_t len);

	// Session secret from the join code (80 bits).
	constexpr size_t kSecretSize = 10;

	// PRF(secret, label, extra) -> 64 bits. Key = secret || "W4P1KD"; message = label || 0x00 || extra.
	uint64_t Prf(const uint8_t secret[kSecretSize], const char* label, const void* extra, size_t extra_len);

	// 16-byte key from two PRF outputs (label + "1", label + "2").
	void DeriveKey16(const uint8_t secret[kSecretSize], const char* label, const void* extra, size_t extra_len,
		uint8_t out[16]);

	// Crockford base32 text of bytes (no grouping), used for ICE ufrag/pwd strings (valid ICE characters).
	std::string Base32Plain(const void* data, size_t len);
} // namespace w4p
