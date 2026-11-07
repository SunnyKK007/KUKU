#!/bin/sh
# Rebuild the PDFs and refill the submission folders.
#   ../1_SUBMIT_THESE_FILES      what you upload (Problem 3)
#   ../2_BACKUP_other_problems   Problems 1 and 2, in case you change your mind
set -e
cd "$(dirname "$0")"
python3 docs/build_pdfs.py
SUB=../1_SUBMIT_THESE_FILES
P1=../2_BACKUP_other_problems/Problem1_promo_finder
P2=../2_BACKUP_other_problems/Problem2_AI_lawyer
mkdir -p "$SUB" "$P1" "$P2"
rm -f "$SUB"/*.pdf "$SUB"/*.zip "$P1"/* "$P2"/*

cp docs/p3_solution.pdf "$SUB/Solution_Doc_Problem3.pdf"
cp docs/p3_video_script.md "$SUB/Video_Script_Problem3.md"
(cd outputs && zip -qr "../$SUB/Raw_Outputs_Problem3.zip" p3 $(ls -d p3_* 2>/dev/null || true))

cp docs/p1_solution.pdf "$P1/Solution_Doc_Problem1.pdf"
cp docs/p1_video_script.md "$P1/Video_Script_Problem1.md"
(cd outputs && zip -qr "../$P1/Raw_Outputs_Problem1.zip" p1 p1_baseline)

cp docs/p2_solution.pdf "$P2/Solution_Doc_Problem2.pdf"
cp docs/p2_video_script.md "$P2/Video_Script_Problem2.md"
(cd outputs && zip -qr "../$P2/Raw_Outputs_Problem2.zip" p2)

echo "Done. Upload the files in 1_SUBMIT_THESE_FILES."
