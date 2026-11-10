# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team:
- Members:
- Provider/model:

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

> 1–2 câu mô tả agent dùng để làm gì (cho team khác hiểu nhanh).

Ví dụ: "Research agent: tìm tin theo từ khóa / theo tài khoản, đọc URL, tổng hợp thành digest, và gửi lên Telegram khi được xác nhận."

**Link dùng thử (deploy):**

> Dán link public để team khác mở thử ngay. Cách deploy nhanh bằng Cloudflare Tunnel xem README. Nếu deploy Vercel/Streamlit Cloud thì dán link đó.
>
> URL: 

## A2. Tool agent có

> Liệt kê các tool agent đang dùng (gồm tool mới nhóm tự thêm). Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin | không |
|  |  |  |
|  |  |  |

## A3. Câu hỏi mẫu để thử

> 3–5 câu hỏi/yêu cầu mẫu để team khác tự thử agent ngay.

1.
2.
3.

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline | Đo hành vi chưa tối ưu trước khi sửa | - | 0.75 | `runs/v0_B_base_openrouter_20261110T101854161775.json` |
| v1 | `system_prompt.md` | Prompt rõ routing/clarify/out-of-scope sẽ nâng case_accuracy | 0.75 | 0.90 | `runs/v1_B_base_openai_20261110T110949070180.json` |
| v2 | `system_prompt.md` | Force `clarify(yes_no)` trước send sẽ PASS R12 | 0.90 | 0.95 | `runs/v2_B_base_openai_20261110T111640723060.json` |
| v3 | `system_prompt.md` | Multi-turn switch source chỉ gọi tool mới sẽ PASS M06 | 0.95 | 1.00 | `runs/v3_B_base_openai_20261110T111728560670.json` |

## B2. Failure Analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| `R08_out_of_scope` | `out_of_scope` | `send(text="Nguyên hàm của x^2 là...")` | `expected no tool call` (`unexpected_tool_call`): câu hỏi giải tích ngoài phạm vi research nhưng model gọi `send` để gửi câu trả lời đi | Thêm rule ngoài phạm vi (`out_of_scope`) vào `system_prompt.md` (từ chối/không gọi tool) và làm rõ mô tả `send` trong `tools.yaml` |
| `R10_missing_handle` | `missing_info` | `timeline(screenname="sama")` | `missing tool call clarify; extra tool call timeline` (`missing_tool_call`): prompt starter xúi đoán bừa Sam Altman khi thiếu tên tài khoản | Xoá chỉ dẫn đoán mò trong `system_prompt.md`, yêu cầu gọi `clarify(response_type="text")` khi thiếu handle/tài khoản |
| `R11_missing_url` | `missing_info` | `fetch(url="https://example.com/article")` | `missing tool call clarify; extra tool call fetch` (`missing_tool_call`): prompt starter xúi tự đoán URL khi user chỉ nói "bài viết này" | Xoá chỉ dẫn đoán URL trong `system_prompt.md`, yêu cầu gọi `clarify(response_type="text")` khi thiếu URL cụ thể |
| `R12_confirm_before_send` | `wrong_boundary` | `send(text="Bản tin này đã được đăng lên Telegram.")` | `missing tool call clarify; extra tool call send` (`missing_tool_call`): prompt starter bảo gửi ngay không cần hỏi xác nhận | Sửa `system_prompt.md` và `tools.yaml`: bắt buộc gọi `clarify(response_type="yes_no")` để xin xác nhận trước khi gọi `send` |
| `R13_parallel_web_and_tweets` | `wrong_tool` | `lookup(query="AI news", timeframe="day")`, `social_search(query="AI", search_type="Latest", limit=5)` | `query: expected 'AI', got 'AI news'; topic: expected 'news', got None` (`wrong_arg_value`): gọi `lookup` tìm tin tức nhưng gộp chữ "news" vào `query` thay vì truyền `topic="news"` và `query="AI"` | Ghi rõ convention của `lookup` trong `tools.yaml` và `system_prompt.md`: khi tìm tin tức thời sự phải đặt `topic="news"` và giữ `query` là chủ đề gốc (`"AI"`), không nhét từ `"news"`/`"tin tức"` vào `query` |

## B3. Team Eval Cases

List the 10 cases added to `data/eval_group.json` (5 single turn + 5 multi turn).

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| `G01_karpathy_timeline` (single) | Map Andrej Karpathy → `karpathy` + timeline | `timeline(screenname="karpathy")` | PASS |
| `G02_arxiv_papers_routing` (single) | Route tới tool mới `papers` | `papers(max_results=3)` | PASS |
| `G03_policy_data_privacy` (single) | Route tới tool mới `policy` | `policy(policy_area="data_privacy")` | PASS |
| `G04_latest_search_type` (single) | Arg `search_type=Latest` cho “mới nhất” | `social_search(query="Claude 4", search_type="Latest")` | PASS |
| `G05_publish_confirm_yes_no` (single) | Confirm trước khi post Telegram | `clarify(response_type="yes_no")` | PASS |
| `G06_multiturn_papers_then_read` (multi) | Switch papers → `paper_text` + `max_pages=2` | `paper_text(arxiv_url="1706.03762", max_pages=2)` | PASS |
| `G07_multiturn_policy_then_news` (multi) | Switch policy → web news AI agents | `lookup(query="AI agents", topic="news", timeframe="day")` | PASS |
| `G08_multiturn_missing_handle_then_sama` (multi) | Fill Sam Altman → `sama`, limit=7 | `timeline(screenname="sama", limit=7)` | PASS |
| `G09_multiturn_top_then_correct_latest` (multi) | Sửa Top → Latest, giữ query Gemini | `social_search(query="Gemini", search_type="Latest")` | PASS |
| `G10_multiturn_two_urls_parallel` (multi) | Parallel fetch 2 URL | `fetch` × 2 URL OpenAI + Anthropic | PASS |

Group run (`v3`, openai): **10/10 PASS**, `case_accuracy=1.0` — `runs/v3_B_group_openai_20261110T122514058305.json`

## B4. Live Chat Evidence

Use `transcripts/*.transcript.json`.

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Bonus Evidence

Only fill if your team did bonus.

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) |  |  |  |
| arXiv/company policy |  |  |  |
| UI |  |  |  |
| Tool unit tests (`tests/`) | `pytest` output |  |  |

Tool unit tests: số test đã viết, số bug tìm được trong tool có sẵn (nếu có), và một ví dụ lỗi mà unit test bắt được nhưng eval không bắt được.

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
- Which fixes belonged in `tools.yaml`?
- Which failure needed manual review instead of automatic grading?
- What would you improve next?

## B7. Small Local Model Challenge (bonus)

Only fill if your team did the local model challenge.

| Version | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
|---|---|---|---|---|---|---|---|
| v3 | (cloud) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v4-local |  |  |  |  |  |  |  |
| v5-local |  |  |  |  |  |  |  |

Lỗi đặc thù của model nhỏ (đếm từ run JSON):

| Failure Pattern | Count | Example Case | Fix Tried | Helped? |
|---|---|---|---|---|
| wrong / hallucinated tool |  |  |  |  |
| invalid JSON args (`_invalid_json_arguments`) |  |  |  |  |
| no tool call / answered directly |  |  |  |  |
| missed `clarify` |  |  |  |  |
| repeated / unnecessary calls |  |  |  |  |

- Cái gì giúp model nhỏ gọi tool đúng hơn nhất? Bằng chứng?
- Bản prompt tối ưu cho local chạy trên model cloud thì sao?
- Khi nào nhóm sẽ chọn model local thay vì cloud cho agent này?
