#!/usr/bin/env bash
# Auto-flash daemon for the BSides DSM badge (CH585 / ch32fun).
#
# WCH chips flash over their USB bootloader, NOT the run-mode CDC port
# (/dev/tty.usbmodem0071). This watcher polls for a CH585 in bootloader mode
# and flashes the current firmware the moment one appears, then waits for it to
# disconnect before re-arming so each plugged-in board is flashed exactly once.
#
# Usage:
#   ./flash-daemon.sh            # build once, then watch & flash forever
#   ./flash-daemon.sh --no-build # skip the initial build (use existing .bin)
#
# Stop with Ctrl-C.

set -u

cd "$(dirname "$0")"

MINICHLINK="./ch32fun/minichlink/minichlink"
POLL_INTERVAL=1
# Token the running firmware listens for on its USB-CDC port to enter the ISP
# bootloader (see handle_usbfs_input() in bsidesdsmbadge.c).
BOOT_TOKEN="BOOTSEL"

log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }

# Returns 0 if a CH585 bootloader is currently present.
bootloader_present() {
	"$MINICHLINK" -l 2>&1 | grep -q "Found MCU in bootloader mode"
}

# Ask any running badge (CDC serial port) to jump into the bootloader.
try_trigger_bootloader() {
	local port found=0
	for port in /dev/cu.usbmodem*; do
		[[ -e "$port" ]] || continue
		# Skip the WCH bootloader's own CDC if present; harmless to write to app ports.
		printf '%s' "$BOOT_TOKEN" > "$port" 2>/dev/null && found=1
	done
	return $((1 - found))
}

# Build the flasher if missing.
if [[ ! -x "$MINICHLINK" ]]; then
	log "Building minichlink..."
	make -C ch32fun/minichlink all || { log "Failed to build minichlink"; exit 1; }
fi

# Build firmware once up front (unless told not to).
if [[ "${1:-}" != "--no-build" ]]; then
	log "Building firmware..."
	if ! make build >/tmp/flash-daemon-build.log 2>&1; then
		log "Build FAILED — see /tmp/flash-daemon-build.log"
		exit 1
	fi
	log "Build OK ($(ls -la bsidesdsmbadge.bin | awk '{print $5}') bytes)"
fi

log "Watching for CH585 in bootloader mode... (Ctrl-C to stop)"
log "Running badges are auto-sent the '$BOOT_TOKEN' token to enter ISP."
log "(First-ever install still needs one manual bootloader entry via BOOT pin or SWIO.)"

armed=1
while true; do
	if bootloader_present; then
		if [[ "$armed" -eq 1 ]]; then
			log "Bootloader detected — flashing..."
			if make flash >/tmp/flash-daemon-flash.log 2>&1; then
				log "FLASH OK"
			else
				log "FLASH FAILED — see /tmp/flash-daemon-flash.log"
			fi
			armed=0
			log "Waiting for board to disconnect before re-arming..."
		fi
	else
		if [[ "$armed" -eq 0 ]]; then
			log "Board disconnected — re-armed, ready for next board."
			armed=1
		fi
		# Not in bootloader: if a running badge is present, nudge it into ISP.
		if [[ "$armed" -eq 1 ]] && ls /dev/cu.usbmodem* >/dev/null 2>&1; then
			if try_trigger_bootloader; then
				log "Sent '$BOOT_TOKEN' to running badge — waiting for bootloader..."
			fi
		fi
	fi
	sleep "$POLL_INTERVAL"
done
