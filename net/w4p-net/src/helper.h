// SPDX-License-Identifier: GPL-3.0-or-later
// w4p-net helper: ICE links (libjuice, MUX mode) between up to 4 PCs, and a loopback bridge to the local emulator.
// Design: docs/research/m5_connection_design.md (option S). Results: docs/research/m5_w4pnet_results.md.
#pragma once

#include "codec.h"

#include <array>
#include <atomic>
#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <string>
#include <thread>
#include <vector>

#include <juice/juice.h>

namespace w4p
{
	constexpr int kMaxSlots = 4;
	constexpr uint8_t kNoSlot = 0xFF;
	constexpr int kHelperProto = 1;

	struct Options
	{
		bool host = false;
		std::string join_text;          // joiner: text containing the join code
		int players = 4;                // host: 2..4
		std::string bind_addr;          // ICE socket bind address; empty = all interfaces
		int ice_port = 41500;           // fixed UDP port for all ICE agents (MUX); tries +1..+19 if busy
		bool stun = true;
		std::string stun_host = "stun.cloudflare.com";
		int stun_port = 3478;
		int emu_port = 41000;           // emulator ListenPort (W4P BindAddress must be 127.0.0.1)
		int slot_port_base = 41100;     // helper loopback ports base..base+3 (W4P Peer<p> = 127.0.0.1:base+p)
		std::string log_path = "connection-log.txt";
		std::string stats_path;         // optional JSON with final statistics
		int want_slot = -1;             // joiner: requested slot (1..3), -1 = any
		double max_seconds = 0;         // 0 = no limit
		int connect_minutes = 10;       // keep re-creating failed agents this long
		bool verbose = false;
		bool read_stdin = true;
		// test switches (single-PC tests only)
		bool test_no_direct_dial = false;     // host: ignore path (b) requests (forces reply codes)
		std::vector<int> test_block_peers;    // joiner: no direct link to these slots (forward through the host)
	};

	struct SlotStats
	{
		std::atomic<uint64_t> data_tx{0}, data_rx{0}, data_tx_bytes{0}, data_rx_bytes{0}, data_no_route{0};
		std::atomic<uint64_t> data_tx_via_host{0}, data_rx_via_host{0};
		std::atomic<uint64_t> probe_tx{0}, probe_rx{0}, probe_rx_dup{0}, probe_echo_rx{0}, probe_no_route{0};
		std::atomic<uint64_t> probe_tx_via_host{0};
		std::mutex mx;                       // guards the vectors below
		std::vector<uint8_t> probe_seen;     // received probe sequence numbers
		std::vector<float> probe_rtt_ms;     // echo round-trip times
	};

	class Helper;

	struct Link
	{
		enum class Kind
		{
			HostToJoiner,
			JoinerToHost,
			Pair,
		};
		Helper* owner = nullptr;
		int index = 0;
		Kind kind = Kind::HostToJoiner;
		std::atomic<int> peer_slot{kNoSlot};
		std::array<uint8_t, kNonceSize> nonce{};
		bool controlling = false;
		std::string lufrag, lpwd, rufrag, rpwd;
		std::vector<Candidate> remote_cands; // from a code / introduction (empty: path b or test block)
		bool remote_end = true;              // add a=end-of-candidates
		uint8_t key[16] = {};
		bool blocked = false;                // test switch: no direct traffic on this link
		char path = '?';                     // host: 'a' reply code, 'b' direct dial; pairs: 'i' introduced

		std::shared_mutex agent_mx;          // shared: juice_send; exclusive: swapping the agent pointer
		std::atomic<juice_agent_t*> agent{nullptr};
		std::atomic<int> state{JUICE_STATE_DISCONNECTED};
		std::atomic<int64_t> state_us{0};
		std::atomic<int64_t> conn_cb_us{0}; // first CONNECTED/COMPLETED of the current agent (callback time)
		std::atomic<bool> gathering_done{false};
		int seen_state = -1;                 // main thread: last logged state
		int attempts = 0;
		int64_t first_start_us = 0, agent_start_us = 0, connected_us = 0, lost_us = 0;
		bool ever_connected = false, gave_up = false;
		std::string sel_local, sel_remote;   // selected pair description (masked)

		// host side, after HELLO
		bool welcomed = false;
		std::vector<Candidate> peer_desc;
		int want_slot = -1;
		// joiner side STATUS received by the host
		uint8_t status_ready = 0;
		std::array<uint8_t, kMaxSlots> status_route{};
		std::array<uint16_t, kMaxSlots> status_rtt{};

		std::atomic<uint64_t> tx{0}, tx_bytes{0}, rx{0}, rx_bytes{0}, bad_tag{0}, bad_mac{0}, bad_src{0};
		std::atomic<uint64_t> fwd_out{0}, send_err{0};
		std::atomic<uint32_t> ping_seq{0}, pongs{0};
		std::mutex rtt_mx;
		std::vector<float> ping_rtt_ms;

		bool Connected() const
		{
			const int s = state.load();
			return s == JUICE_STATE_CONNECTED || s == JUICE_STATE_COMPLETED;
		}
	};

	class Helper
	{
	public:
		explicit Helper(const Options& o);
		~Helper();
		int Run(); // returns the process exit code

		// libjuice callbacks (static trampolines)
		static void CbState(juice_agent_t* a, juice_state_t s, void* user);
		static void CbCandidate(juice_agent_t* a, const char* sdp, void* user);
		static void CbGatheringDone(juice_agent_t* a, void* user);
		static void CbRecv(juice_agent_t* a, const char* data, size_t size, void* user);
		static void CbMuxIncoming(const juice_mux_binding_request_t* info, void* user);

	private:
		struct Incoming
		{
			std::string local_ufrag, remote_ufrag, address;
			uint16_t port = 0;
		};
		struct CtrlMsg
		{
			Link* link = nullptr;
			uint8_t src = kNoSlot;
			std::vector<uint8_t> body;
		};
		struct Intro
		{
			int a = 0, b = 0;
			Link* la = nullptr;
			Link* lb = nullptr;
			std::array<uint8_t, kNonceSize> nonce{};
			bool ack_a = false, ack_b = false;
			int64_t last_send_us = 0;
		};

		// setup
		bool OpenMux();
		bool GatherHostCandidates(std::vector<Candidate>* out);
		bool OpenBridge();
		void CloseBridge();

		// links
		Link* NewLink(Link::Kind kind);
		void StartAgent(Link* L);
		void StopAgent(Link* L);
		void SetupHostJoinerCreds(Link* L, bool host_side);
		void SetupPairCreds(Link* L, int my, int peer);
		std::vector<Candidate> LocalCandidates(juice_agent_t* a);
		Link* FindByNonce(const std::array<uint8_t, kNonceSize>& n);
		int FreeSlot(int want) const;

		// data path
		size_t Wrap(uint8_t* out, uint8_t type, uint8_t src, uint8_t dst, uint8_t flags, const uint8_t key[16],
			const void* payload, size_t n) const;
		bool SendRaw(Link* L, const uint8_t* buf, size_t n);
		bool SendTo(int dst, uint8_t type, const void* payload, size_t n, bool* via_host);
		bool SendCtrl(Link* L, const std::vector<uint8_t>& body);
		Link* Route(int dst, bool* via_host);
		void OnRecv(Link* L, const uint8_t* data, size_t size);
		void DeliverToEmu(int src, const uint8_t* p, size_t n);
		void BridgeThread();
		void ProbeThread(double rate, int size, double seconds);

		// main loop parts
		void Tick();
		void HandleCommand(const std::string& line);
		bool Muted(int slot) const;           // test switch "mute" (T1g): game data to/from this slot dropped now?
		void HandlePaste(const std::string& line);
		void HandleIncoming(const Incoming& in);
		void HandleCtrl(const CtrlMsg& m);
		void CheckLinks();
		void HostIntroductions();
		void SendRoster();
		void JoinerStatus();
		void Pings();
		void ReadyCheck();
		void Summary(bool final);
		std::string StatsJson();
		uint8_t RouteState(int slot);

		Options opt_;
		bool is_host_ = false;
		int ice_port_ = 0;
		bool include_loopback_ = false;
		std::array<uint8_t, kSecretSize> secret_{};
		uint8_t tag_[8] = {};
		std::array<uint8_t, kNonceSize> my_nonce_{}; // joiner
		std::vector<Candidate> host_cands_;          // joiner: from the join code
		std::vector<Candidate> my_cands_;            // own candidates (for codes / HELLO)
		std::string join_code_, reply_code_;
		int64_t t0_us_ = 0;
		int64_t start_us_ = 0;

		std::vector<std::unique_ptr<Link>> links_;   // main thread only; never erased
		std::array<std::atomic<Link*>, kMaxSlots> slot_link_{};
		std::atomic<int> my_slot_{kNoSlot};
		std::atomic<uint8_t> occupied_{0};           // bit per slot
		int players_ = 4;
		bool lobby_open_ = true;

		std::mutex q_mx_;
		std::deque<std::string> commands_;
		std::deque<Incoming> incoming_;
		std::deque<CtrlMsg> ctrl_;
		std::atomic<bool> quit_{false};

		// bridge
		std::array<uintptr_t, kMaxSlots> slot_sock_{};
		std::thread bridge_thread_, stdin_thread_, probe_thread_;
		std::atomic<bool> bridge_stop_{false};
		std::atomic<uint64_t> loop_strangers_{0}, emu_tx_{0}, emu_rx_{0}, emu_drop_{0};

		// test switch (T1g outage): "mute SECONDS [SLOT]" drops the game data (type D) to and from SLOT (all other
		// slots without SLOT) until mute_until_us_; control traffic, pings and ICE keep running
		std::atomic<int64_t> mute_until_us_{0};
		std::atomic<uint8_t> mute_mask_{0};
		std::atomic<uint64_t> mute_drop_tx_{0}, mute_drop_rx_{0}, mute_count_{0};

		// probe
		std::atomic<bool> probe_running_{false};
		std::atomic<uint32_t> probe_seq_{0};
		std::array<SlotStats, kMaxSlots> slot_stats_;
		double probe_rate_ = 0;
		int probe_size_ = 0;
		double probe_seconds_ = 0;
		int64_t probe_start_us_ = 0, probe_end_us_ = 0;
		bool probe_done_reported_ = true;

		// host bookkeeping
		std::vector<Intro> intros_;
		int64_t last_ping_us_ = 0, last_status_us_ = 0, last_summary_us_ = 0, last_hello_us_ = 0, last_roster_us_ = 0;
		bool ready_ = false;
		bool welcomed_ = false; // joiner
		std::vector<std::string> incoming_seen_;
		uint64_t strangers_ = 0;
	};
} // namespace w4p
