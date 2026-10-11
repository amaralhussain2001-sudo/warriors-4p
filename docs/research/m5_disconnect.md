# M5: disconnect handling in the W4P lockstep (protocol 3, build w4p-m5-1), 2026-10-11

Policy (BRIEF 4.6, docs/plan/M5.md criteria 3-5): when a player's connection drops, everyone freezes with a 60 s
countdown; if he is back in time play continues; otherwise the host chooses "continue without him" or "restart from the
last checkpoint without him"; if the host leaves, the session ends. Code: fork `pcsx2/W4P/W4P.cpp` (DisconnectTick,
ApplyDrop, SendRelay, ScheduleCalls). Status of each claim: design + code = this note; runtime results in FINDINGS.

## Why it needs a protocol
Lockstep: an instance runs poll t only when it has every player's input for t. When a player's packets stop, each
remaining instance stalls at the first poll it lacks - and those polls can differ by a few polls (each instance got his
inputs up to a different poll before the loss). Dropping him must give **every** remaining instance exactly the same
inputs: his real inputs before a common poll T, neutral input from T on. Late inputs that arrive at only some
instances after the timeout must be ignored.

## Mechanism
1. **Gone vs. behind.** A player is "gone" when nothing at all was received from him for 2 s (`last_rx_ms`); a player
   who is only behind keeps sending inputs/hashes/hellos. The countdown runs from his last packet.
2. **Countdown.** While stalled, every instance shows "Waiting for Player N... 37s" and sends a status packet every
   250 ms: the poll it is stalled at and whether the timeout has passed here (`PktStatus`).
3. **Back in time.** If his packets return before the timeout, the stalled polls complete and play continues; nothing
   else happens (the normal lockstep path).
4. **Timeout.** At the timeout each instance stops accepting input packets from him (`no_accept`), so nobody can run
   further with his late inputs. Non-hosts show "Player N did not come back. Waiting for the host's choice...".
5. **Host's choice.** The host (slot 0) sees "Press Cross: continue without Player N. Press Circle: restart from the last
   checkpoint without Player N." (his own controller, read directly while the game is frozen). The choice is accepted
   only when every other remaining player has reported "timeout passed" in a status packet less than 2 s old.
6. **Common drop poll.** T = the furthest stall poll among the remaining instances (host's own and the status packets).
   That instance already ran every poll before T with his real inputs, so it holds them.
7. **Announcement and relay.** The host applies the drop and repeats `PktDrop{player, choice, T}` every 250 ms for 5 s;
   every instance that applies it repeats it too (a lost datagram is covered). Each also sends `PktRelay`: the leaving
   player's inputs it holds for [T-64, T). Receivers store missing ones (inputs never change once sent, first value
   wins). Then every remaining instance has his real inputs for all polls < T and neutral input from T on.
8. **Game side.** At poll T (+ offset) every instance makes the same game call through the call mailbox (`LeaveCalls` or
   `RestartCalls`, arguments P = his game player index, H = his handle, GM / GM+0x.. = GameMgr), so the game removes
   his character or restarts the level identically everywhere. The calls to use come from the session-policy research
   (`docs/research/session_policies.md`); without them his character simply stands still (neutral input).
9. **Afterwards.** Packets from a dropped player are ignored; hash comparisons skip him; nothing is sent to him.
10. **Host leaving.** If the host is the one gone, the others show "The host (Player 1) has left. The session is over -
    you can close the game." and stay frozen (closing the window works: the wait loop lets the VM stop).

## Settings (W4P ini)
| Key | Meaning |
|---|---|
| `DisconnectTimeoutS` | countdown length, default 60 (3-600) |
| `LeaveCalls` / `RestartCalls` | `offset:fn:args` items, comma separated (e.g. `0:00160D78:GM+0x124` = MenuLoadLevel) |
| `TestDrop` | test only: `poll:seconds` - this instance stops sending and drops everything it receives from session poll `poll` for `seconds` (0 = for good) |
| `TestHostChoice` | test only: `continue` or `restart` - the host decides by itself once the others are ready |

## Limits (HYPOTHESIS until tested)
- One player is dropped at a time (a second gone player is handled by the next round of the same logic).
- The relay window is 64 polls; stall points differ by at most input delay + 1 polls in this lockstep.
- A player who comes back after the timeout cannot rejoin the running mission (policy: rejoin from the lobby).
