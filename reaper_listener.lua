-- BIO-CHUGGER REAPER LISTENER
-- This script helps monitor if the Bio-Chugger app is broadcasting.
-- Note: You MUST configure REAPER OSC first as described in README.md.

function main()
  -- If REAPER OSC is set to port 8000 and mapped to /tempo, 
  -- the project tempo will change automatically.
  -- This script is a placeholder for additional custom logic.
  
  -- Example: Add a console message when tempo changes
  local current_bpm = reaper.Master_GetTempo()
  if last_bpm and current_bpm ~= last_bpm then
    reaper.ShowConsoleMsg("Biological Pulse Sync: " .. current_bpm .. " BPM\n")
  end
  last_bpm = current_bpm
  
  reaper.defer(main)
end

reaper.ShowConsoleMsg("--- BIO-CHUGGER LINK ACTIVE ---\n")
main()
