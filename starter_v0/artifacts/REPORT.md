# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team: PhamTruongChinh-2A202603426
- Members: Phạm Trường Chinh-2A202603426, Nguyễn Minh Quân-2A202603510, Nguyễn Văn Ba-2A202603489, Phạm Trung Kiên-2A202603479, Nguyễn Thanh Tùng-2A202603446
- Provider/model: OpenAI

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

> 1–2 câu mô tả agent dùng để làm gì (cho team khác hiểu nhanh).

 Agent hỗ trợ tìm tin AI, theo dõi Twitter/X, đọc URL, tìm/đọc paper arXiv, tra policy và gửi bản tin Telegram sau xác nhận

Ví dụ: "Research agent: tìm tin theo từ khóa / theo tài khoản, đọc URL, tổng hợp thành digest, và gửi lên Telegram khi được xác nhận."

**Link dùng thử (deploy):**

> Dán link public để team khác mở thử ngay. Cách deploy nhanh bằng Cloudflare Tunnel xem README. Nếu deploy Vercel/Streamlit Cloud thì dán link đó.
>
> URL: 

## A2. Tool agent có

> Liệt kê các tool agent đang dùng (gồm tool mới nhóm tự thêm). Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận | không |
| timeline | lấy bài đăng gần đây từ một tài khoản X/Twitter | không |
| social_search | tìm bài đăng X/Twitter theo chủ đề | không |
| lookup | tìm thông tin và tin tức trên web | không |
| fetch | đọc nội dung một URL web | không |
| format | định dạng dữ liệu đã có thành bản tin | không |
| send | gửi Telegram sau khi người dùng xác nhận | không |
| policy | tra cứu chính sách nội bộ | không |
| papers | tìm paper trên arXiv | không |
| paper_text | trích xuất văn bản từ PDF paper arXiv | không |
| hackernews | tìm bài Hacker News, điểm và số bình luận | có |
| github_repos | tìm repository GitHub theo chủ đề và ngôn ngữ | có |
| wikipedia | lấy phần giới thiệu bài Wikipedia | có |
| hf_models | tìm model Hugging Face theo tên hoặc tác vụ | có |

## A3. Câu hỏi mẫu để thử

> 3–5 câu hỏi/yêu cầu mẫu để team khác tự thử agent ngay.

1.Lấy 5 tweet mới nhất của Andrej Karpathy.

2.Tìm 3 paper arXiv về tool-calling evaluation.

3.Tóm tắt vài tweet mới nhất giúp mình.

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

Bằng chứng chính:

- Transcript T1: `transcripts/v3_openai_20261110T051320715159.transcript.json`
- Transcript T2: `transcripts/v3_openrouter_20261110T112555195843.transcript.json`
- Cả hai có artifact version: `v3+p933b11f24ccb+t0fb36ba058b9`.
- T1 sử dụng OpenAI / `gpt-4o-mini`; T2 sử dụng OpenRouter / `openai/gpt-4o-mini`.

| Transcript / Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| T1 / 3 | Tin AI hôm nay có gì nổi bật? | `lookup(query="AI", topic="news", timeframe="day", max_results=5)` | v3 / prompt `933b11f24ccb` | Tool trả về 5 item; agent tổng hợp thành câu trả lời có liên kết nguồn. |
| T2 / 1 | Tóm tắt vài tweet mới nhất giúp mình | `clarify(response_type="text")` | v3 / prompt `933b11f24ccb` | Agent hỏi tài khoản cần theo dõi và chuyển sang trạng thái `waiting_for_user`. |
| T1 / 4–5 | Tóm tắt vài tweet mới nhất → Tài khoản X của Sam Altman | Hỏi lại bằng văn bản, sau đó gọi `timeline(screenname="sama", limit=5)` | v3 / prompt `933b11f24ccb` | Agent sử dụng thông tin bổ sung, map đúng handle và nhận 5 bài đăng. Lượt hỏi lại chưa dùng tool `clarify`. |
| T1 / 7 | Tìm 3 bài báo arXiv gần đây về AI agent evaluation | `papers(query="AI agent evaluation", max_results=3, sort_by="lastUpdatedDate")` | v3 / prompt `933b11f24ccb` | Tool trả về 3 paper. Cần kiểm tra thủ công độ liên quan; đủ số lượng chưa đồng nghĩa đúng chủ đề. |
| T1 / 8–9 | Gửi bản tin AI vừa rồi lên Telegram → có | Hỏi xác nhận bằng văn bản; sau đó runtime thực thi `send(confirmed=false)` | v3 / prompt `933b11f24ccb` | Bản nháp được giữ ở trạng thái `needs_confirmation`, chưa gửi ra ngoài. |
| T1 / 10 | Người dùng bấm Confirm & Send Telegram | `send(confirmed=true)` | v3 / prompt `933b11f24ccb` | Tool trả `status="sent"` và `message_id=13`, chứng minh đã gửi thành công. |

### Nhận xét

Live chat chứng minh agent có thể tìm dữ liệu, sử dụng thông tin bổ sung và thực hiện luồng gửi Telegram có xác nhận.

Tuy nhiên, hành vi chưa hoàn toàn nhất quán: cùng tình huống thiếu tài khoản, agent có lúc gọi `clarify`, có lúc chỉ hỏi bằng văn bản. Với yêu cầu tóm tắt bài đăng từ tài khoản, việc gọi `fetch` trên URL hồ sơ cũng cần được review để xác định có nên chuyển sang `timeline`.

Kết quả live chat cần được đánh giá cùng nội dung tool trả về, không chỉ dựa vào trạng thái `answered`.

## B5. Bonus Evidence

| Hạng mục | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Gửi Telegram có xác nhận | `transcripts/v3_openai_20261110T051320715159.transcript.json`, turn 9–10 | Runtime giữ bản nháp trước khi người dùng bấm xác nhận; lần gửi cuối trả `status="sent"`. | Không tin trực tiếp giá trị `confirmed=true` do model tạo ra; việc gửi phải đi qua cơ chế xác nhận của runtime/UI. |
| Tìm paper arXiv | Transcript trên, turn 7 | `papers` nhận đúng số lượng yêu cầu và trả 3 paper. | Cần kiểm tra độ liên quan và phân biệt abstract với nội dung toàn văn; không coi kết quả tìm kiếm là bằng chứng đã đọc paper. |
| Tra cứu policy nội bộ | `data/eval_group.json`, case G03; `runs/v3_B_group_openai_20261110T122514058305.json` | Model route đúng tới `policy(policy_area="data_privacy")`. | PASS routing chưa chứng minh câu trả lời cuối diễn giải policy chính xác. |
| UI | `app.py`; transcript trên, turn 10 | Có thao tác `[UI] Confirm & Send Telegram` được ghi vào transcript và gửi thành công. | Transcript chứng minh luồng thao tác đã chạy; cần bổ sung link public đang hoạt động vào phần A. |
| Unit test Telegram | `tests/test_send_telegram.py` | Có 10 test kiểm tra xác nhận, thiếu cấu hình, lỗi API, hủy gửi, chống gửi trùng, giới hạn độ dài và timeout. | Đây là bằng chứng về mã test; chưa có output chạy pytest được dẫn trong báo cáo để kết luận toàn bộ suite pass. |
| Tool Unit Test Challenge | `tests/test_tools_todo.py` | Đã có 2 test thực thi cho gửi Telegram thành công và thiếu cấu hình. | Còn 15 test stub dùng `pytest.skip(TODO)`; chưa đạt yêu cầu 0 skipped và chưa đủ bằng chứng hoàn thành test cho tool mới. |

### Phân biệt unit test và model eval

Model eval kiểm tra agent chọn đúng tool và truyền đúng arguments. Unit test kiểm tra implementation của tool có xử lý arguments, gọi API và trả kết quả đúng hay không.

Ví dụ, `test_lookup_sends_expected_request_and_maps_results` trong `tests/test_tools_examples.py` kiểm tra request thực tế có `topic`, `time_range` và `max_results`. Nếu model truyền đúng `timeframe="day"` nhưng implementation quên đưa `time_range` vào HTTP request, model eval vẫn có thể PASS trong khi unit test này sẽ phát hiện lỗi.

Đây là ví dụ về loại lỗi unit test có thể bắt; chưa có bằng chứng để khẳng định nhóm đã phát hiện và sửa một bug như vậy.

### Trạng thái kiểm thử

- Các test đã triển khai chạy thành công, không có test fail (`0 failed`).
- Các test còn `skip` chưa được tính là đã kiểm tra thành công; cần hoàn thiện để đạt yêu cầu `0 skipped`.
- Chưa ghi nhận bug có sẵn được phát hiện và sửa kèm regression test.
- Các tool có sẵn trong starter không được tính là tool mới.

## B6. Reflection

### Những sửa đổi thuộc `system_prompt.md`

Các quy tắc điều phối chung phù hợp để đặt trong system prompt:

- Không tự đoán tài khoản, URL hoặc paper ID khi thiếu dữ liệu.
- Hỏi lại bằng `clarify` khi thông tin cần thiết chưa có.
- Phân biệt yêu cầu trong phạm vi research với câu hỏi ngoài phạm vi.
- Dùng thông tin các lượt trước để bổ sung arguments cho yêu cầu mới nhất.
- Bỏ yêu cầu cũ khi người dùng chuyển nguồn hoặc sửa yêu cầu.
- Yêu cầu xác nhận trước khi gửi nội dung ra ngoài.

Hai thay đổi có bằng chứng rõ trong chuỗi run ở B1 là: v2 làm rõ `clarify(response_type="yes_no")` cho xác nhận gửi; v3 yêu cầu bỏ tool thuộc nguồn đã bị hủy, giúp sửa lỗi gọi thừa `social_search` ở M06.

V1 sửa nhiều quy tắc cùng lúc nên chưa thể tách riêng đóng góp của từng quy tắc vào mức tăng điểm.

### Những sửa đổi thuộc `tools.yaml`

Các quy ước riêng của từng tool nên đặt ngay trong declaration:

- `timeline.screenname`: handle không có ký tự `@`.
- `social_search.search_type`: phân biệt `Top` và `Latest`.
- `lookup.topic`: dùng `news` khi tìm tin tức.
- `lookup.timeframe`: mô tả rõ `day`, `week`, `month`, `year`.
- `send.confirmed`: chỉ có giá trị true sau khi người dùng xác nhận đúng nội dung cần gửi.
- Mỗi tool cần mô tả rõ khi nào dùng và khi nào không dùng.

Trong repo hiện tại, nhiều description vẫn còn ngắn và chung chung. Vì vậy, phần này là hướng cần hoàn thiện thêm; không nên khẳng định toàn bộ declaration đã được tối ưu.

### Những trường hợp cần review thủ công

1. **Tool call đúng nhưng tool thực thi lỗi.** Trong group run, G02 được chấm PASS về routing/arguments dù `papers` trả `ReadTimeout`. Điểm eval không phản ánh đầy đủ việc hoàn thành nhiệm vụ.
2. **Tìm được paper nhưng chưa chắc đúng chủ đề.** Cần đọc tiêu đề, abstract và đánh giá độ liên quan trước khi kết luận kết quả hữu ích.
3. **Hỏi lại bằng văn bản thay vì `clarify`.** Người dùng vẫn có thể hiểu câu hỏi, nhưng hành vi không khớp contract mà eval yêu cầu.
4. **Xác nhận gửi nội dung.** Cần kiểm tra người dùng đã nhìn thấy đúng bản nháp và đúng đích gửi; một câu “có” không tự chứng minh toàn bộ luồng xác nhận an toàn.

Ngoài ra, các run v1–v3 đang được dẫn ở B1 có tool result báo thiếu API key. Điểm của chúng vẫn có ý nghĩa đối với routing/arguments, nhưng không đủ để khẳng định tool đã lấy dữ liệu thành công.

### Hạn chế của kết quả

- Chuỗi B1 hiện chuyển từ OpenRouter ở v0 sang OpenAI ở v1–v3, làm hạn chế khả năng quy toàn bộ mức tăng cho thay đổi prompt.
- Base eval được dùng nhiều lần để tối ưu nên có nguy cơ prompt phù hợp quá mức với các case đã biết.
- Multiturn eval hiện ghép các lượt trước thành ngữ cảnh cho một lần gọi model; chưa tương đương toàn bộ hội thoại tương tác thực tế.
- Điểm 100% chỉ áp dụng cho các case, arguments được chấm và artifact hash của run tương ứng.
- Prompt hiện tại khác snapshot v3 đã lưu; cần gắn kết quả với đúng snapshot/hash.

### Hướng cải thiện tiếp theo

- Đo riêng tỷ lệ routing đúng, arguments đúng, tool thực thi thành công và nhiệm vụ hoàn thành.
- Bổ sung case mới chưa dùng để chỉnh prompt.
- Hoàn thiện description và convention arguments trong `tools.yaml`.
- Bổ sung unit test cho input biên, timeout, thiếu key và dữ liệu trả về không hợp lệ.
- Chạy lại cùng provider/model và snapshot cố định để so sánh nhất quán.
- Kiểm tra thủ công độ liên quan của nguồn, chất lượng tổng hợp và tính chính xác của trích dẫn.

## B7. Small Local Model Challenge (bonus)

**Trạng thái: đã có transcript thử nghiệm Ollama, nhưng chưa đủ bằng chứng hoàn thành challenge.**

Repo có các transcript `v3_ollama_*.transcript.json`. Tuy nhiên, chưa có run JSON base eval qua Ollama trong thư mục `runs/`, chưa có bằng chứng chạy ít nhất hai model local và hai vòng tối ưu `v4-local`, `v5-local`.

| Version | Model / Provider | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Evidence |
|---|---|---|---|---|---|---|---|
| v3 cloud | gpt-4o-mini / OpenAI | `v3+p933b11f24ccb+t0fb36ba058b9` | 1.00 | 1.00 | 1.00 | 1.00 | `runs/v3_B_base_openai_20261110T111728560670.json`; điểm routing/arguments, tool results còn lỗi thiếu key |
| v3 local | Ollama, chưa tổng hợp model từ transcript | Chưa đối chiếu hash | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Có transcript thử nghiệm, chưa có base eval run |
| v4-local | Chưa có bằng chứng | Chưa có bằng chứng | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa có run JSON |
| v5-local | Chưa có bằng chứng | Chưa có bằng chứng | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa có run JSON |

### Kết luận hiện tại

Chưa đủ dữ liệu để đếm các lỗi đặc thù của model nhỏ hoặc kết luận thay đổi prompt nào giúp model local gọi tool tốt hơn. Không thể dùng transcript thử nghiệm đơn lẻ thay cho bảng so sánh base eval.

Để hoàn thành challenge, cần chạy cùng snapshot v3 trên ít nhất hai model local, tối ưu thêm hai vòng, ghi đầy đủ run JSON và version log, sau đó kiểm tra ngược prompt tối ưu local trên model cloud.

Model local là phương án đáng thử khi cần giảm chi phí gọi model hoặc giữ suy luận trên máy. Tuy nhiên, nếu agent vẫn gọi các API tìm kiếm bên ngoài thì toàn bộ hệ thống chưa hoạt động offline. Quyết định sử dụng cần dựa trên độ chính xác và độ trễ đo được trên máy thực tế.
