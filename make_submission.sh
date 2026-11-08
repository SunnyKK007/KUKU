#!/bin/sh
# Rebuild the PDFs and refill ../1_SUBMIT_THESE_FILES.
#   Upload_this_folder_to_Drive/   share this ONE folder: all three problems
#   Video_scripts_for_you/         outlines for recording, not for upload
set -e
cd "$(dirname "$0")"
python3 docs/build_pdfs.py
SUB=../1_SUBMIT_THESE_FILES
DRIVE="$SUB/Upload_this_folder_to_Drive"
P3="$DRIVE/Problem3_Continuity_Checker"
P1="$DRIVE/Problem1_Promo_Finder"
P2="$DRIVE/Problem2_AI_Lawyer"
VID="$SUB/Video_scripts_for_you"
rm -rf "$DRIVE" "$VID"
mkdir -p "$P3" "$P1" "$P2" "$VID"

cp docs/p3_solution.pdf "$P3/Solution_Doc_Problem3.pdf"
(cd outputs && zip -qr "../$P3/Raw_Outputs_Problem3.zip" p3 $(ls -d p3_* 2>/dev/null || true))
cp docs/p1_solution.pdf "$P1/Solution_Doc_Problem1.pdf"
(cd outputs && zip -qr "../$P1/Raw_Outputs_Problem1.zip" p1 p1_baseline $(ls -d p1_model 2>/dev/null || true))
cp docs/p2_solution.pdf "$P2/Solution_Doc_Problem2.pdf"
(cd outputs && zip -qr "../$P2/Raw_Outputs_Problem2.zip" p2 $(ls -d p2_model 2>/dev/null || true))
cp docs/cover_note.txt "$DRIVE/READ_ME_FIRST.txt"
cp docs/p1_video_script.md docs/p2_video_script.md docs/p3_video_script.md "$VID/"

echo "Done. Upload the folder: 1_SUBMIT_THESE_FILES/Upload_this_folder_to_Drive"
