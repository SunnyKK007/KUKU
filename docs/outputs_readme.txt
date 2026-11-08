Problem 3 outputs: continuity checker, run on all 50 episodes

Rules_Only_Results
  The main result. Code checks only, no AI model.
  continuity_report.md            the 15 issues found, with episode, line and quoted evidence
  issues.json, issues.csv         the same issues as data
  show_bible.json                 every speaker and location in the show
  injection_test_heldout.md       planted-typo test on 10 new trials: 44 of 45 caught
  injection_test_v1.md            the first version's test: 17 of 23 caught
  injection_test_tuning_seeds.md  the same test after fixes: 23 of 23 caught
  manual_audit.md                 my hand check of every issue

With_AI_Model_Results
  The same tool with a Gemini model also reading the stories.
  continuity_report.md            the 15 rule issues plus 58 model findings
  issues.json, issues.csv         the same as data
  manual_audit.md                 my hand check: about half the model findings are real

All files except manual_audit.md are unedited tool output.
