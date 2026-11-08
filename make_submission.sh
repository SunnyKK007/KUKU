#!/bin/sh
# Rebuild the PDFs and refill ../1_SUBMIT_THESE_FILES, one folder per form field:
#   Project_Documentation/   the three 2-page solution PDFs   -> "Project documentation" link
#   Output_Documentation/    the three raw-output zips        -> "Output documentation" link
#   Video_scripts_for_you/   outlines for recording, not for upload
set -e
cd "$(dirname "$0")"
python3 docs/build_pdfs.py
SUB=../1_SUBMIT_THESE_FILES
DOCS="$SUB/Project_Documentation"
OUTS="$SUB/Output_Documentation"
VID="$SUB/Video_scripts_for_you"
rm -rf "$DOCS" "$OUTS" "$VID" "$SUB/Upload_this_folder_to_Drive"
mkdir -p "$DOCS" "$OUTS" "$VID"

cp docs/p1_solution.pdf "$DOCS/Problem1_Promo_Finder.pdf"
cp docs/p2_solution.pdf "$DOCS/Problem2_AI_Lawyer.pdf"
cp docs/p3_solution.pdf "$DOCS/Problem3_Continuity_Checker.pdf"
cp docs/cover_note.txt "$DOCS/READ_ME_FIRST.txt"

(cd outputs && zip -qr "../$OUTS/Problem1_Promo_Finder_outputs.zip" p1 p1_baseline $(ls -d p1_model 2>/dev/null || true))
(cd outputs && zip -qr "../$OUTS/Problem2_AI_Lawyer_outputs.zip" p2 $(ls -d p2_model 2>/dev/null || true))
(cd outputs && zip -qr "../$OUTS/Problem3_Continuity_Checker_outputs.zip" p3 $(ls -d p3_model 2>/dev/null || true))
cp docs/cover_note.txt "$OUTS/READ_ME_FIRST.txt"

cp docs/p1_video_script.md docs/p2_video_script.md docs/p3_video_script.md "$VID/"
echo "Done. Share 1_SUBMIT_THESE_FILES/Project_Documentation and 1_SUBMIT_THESE_FILES/Output_Documentation on Drive."
