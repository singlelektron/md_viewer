local root = assert(vim.env.MD_VIEWER_TEST_ROOT)
local directory = assert(vim.env.MD_VIEWER_TEST_DIR)
local capture = directory .. "/messages.jsonl"
local messages = {}
local notifications = {}

vim.opt.runtimepath:append(root .. "/nvim")
vim.o.hidden = true
vim.o.showmode = false
vim.opt.completeopt = { "menu", "menuone" }
vim.opt.shortmess:append("c")
vim.notify = function(message, level) table.insert(notifications, { message = message, level = level }) end
local viewer = require("md_viewer")
local command = { vim.env.MD_VIEWER_TEST_PYTHON, root .. "/tests/test_nvim_bridge.py", "--capture", capture }

local function records()
  local result = {}
  if vim.fn.filereadable(capture) == 0 then return result end
  for _, line in ipairs(vim.fn.readfile(capture)) do
    local ok, record = pcall(vim.json.decode, line)
    if ok then table.insert(result, record) end
  end
  return result
end

local function updates()
  messages = {}
  for _, record in ipairs(records()) do
    if record.capture == "update" then table.insert(messages, record) end
  end
  return messages
end

local function await(condition, description)
  assert(vim.wait(2500, condition, 10), "Timed out: " .. description)
end

local function await_text(text)
  await(function()
    local all = updates()
    return #all > 0 and all[#all].message.text == text
  end, "preview text: " .. text)
  return messages[#messages]
end

local function edit(name)
  vim.cmd.edit(vim.fn.fnameescape(name))
  vim.bo.filetype = "markdown"
end

local function run()
  viewer.setup({ command = command, debounce_ms = 35 })
  edit(directory .. "/saved note.md")
  assert(viewer.start())
  local first = await_text("Saved original.")
  assert(first.message.modified == false)
  assert(first.message.name == directory .. "/saved note.md")
  assert(first.message.version == 1 and first.message.type == "update")

  -- Actual buffer callbacks, without writing the note or manually firing autocmds.
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { "未保存的数学：$x^2 + y^2$", "第二行" })
  local changed = await_text("未保存的数学：$x^2 + y^2$\n第二行")
  assert(changed.message.modified == true)
  assert(changed.message.revision > first.message.revision)
  assert(vim.fn.readfile(directory .. "/saved note.md")[1] == "Saved original.")

  -- Keep Neovim in Insert mode while the pipe snapshot arrives. In particular,
  -- completion-popup changes must not depend on TextChangedI firing.
  local in_insert
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { "" })
  vim.defer_fn(function()
    vim.fn.complete(1, { "completion_math", "completion_other" })
  end, 10)
  local attempts = 0
  local function observe_insert()
    local all = updates()
    in_insert = {
      mode = vim.api.nvim_get_mode().mode,
      popup = vim.fn.pumvisible(),
      current = vim.api.nvim_get_current_line(),
      preview = all[#all] and all[#all].message.text,
    }
    attempts = attempts + 1
    if in_insert.current ~= in_insert.preview and attempts < 200 then
      vim.defer_fn(observe_insert, 10)
      return
    end
    vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "n", false)
  end
  vim.defer_fn(observe_insert, 50)
  vim.api.nvim_feedkeys("i", "xt!", false)
  assert(in_insert and in_insert.mode:sub(1, 1) == "i", "preview must update before leaving Insert mode")
  assert(in_insert.popup == 1, "completion popup must be visible during this check")
  assert(in_insert.current == "completion_math" and in_insert.preview == in_insert.current,
    "completion edits did not reach preview while popup was visible")

  -- Oversized notes stay local, warn once, and can recover without restarting.
  local before_oversized = #updates()
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { string.rep("x", 1024 * 1024 + 1) })
  await(function()
    for _, notification in ipairs(notifications) do
      if notification.message:find("1 MiB preview limit", 1, true) then return true end
    end
    return false
  end, "oversized-note warning")
  assert(#updates() == before_oversized, "oversized note was sent to the child")
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { "Recovered $x$." })
  await_text("Recovered $x$.")

  local original = vim.api.nvim_get_current_buf()
  -- Queue an old note update, then change buffers before its debounce expires.
  vim.api.nvim_buf_set_lines(original, 0, -1, false, { "Stale queued text" })
  vim.cmd.enew()
  vim.bo.filetype = "markdown"
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { "Unnamed note: $z$" })
  -- Starting an already running viewer selects the current buffer as well.
  assert(viewer.start())
  local second = await_text("Unnamed note: $z$")
  assert(second.message.name == "[No Name]")
  assert(second.pid == first.pid, "switch should reuse the window process")
  vim.wait(100)
  for _, record in ipairs(updates()) do
    assert(record.message.text ~= "Stale queued text", "stale buffer timer escaped")
  end

  local other = vim.api.nvim_get_current_buf()
  vim.api.nvim_set_current_buf(original)
  await_text("Stale queued text")
  vim.api.nvim_set_current_buf(other)
  await_text("Unnamed note: $z$")

  -- Whole-buffer reload must refresh even though on_lines is not emitted for it.
  vim.fn.writefile({ "Before reload." }, directory .. "/reload.md")
  edit(directory .. "/reload.md")
  viewer.start()
  await_text("Before reload.")
  vim.fn.writefile({ "Reloaded externally." }, directory .. "/reload.md")
  vim.cmd("edit!")
  await_text("Reloaded externally.")

  -- Stop cancels deferred work; restarting sends a complete new snapshot.
  vim.api.nvim_buf_set_lines(0, 0, -1, false, { "Pending at stop" })
  viewer.stop()
  assert(not viewer.is_running())
  vim.wait(100)
  for _, record in ipairs(updates()) do
    assert(record.message.text ~= "Pending at stop", "stopped timer wrote to child")
  end
  assert(viewer.start())
  local restarted = await_text("Pending at stop")
  assert(restarted.pid ~= first.pid)
  assert(restarted.message.revision == 1)
  viewer.stop()

  -- Nonzero process exit is surfaced, and a later start can reconnect.
  local failing = vim.deepcopy(command)
  table.insert(failing, "--exit-after-update")
  viewer.setup({ command = failing })
  assert(viewer.start())
  await(function() return not viewer.is_running() end, "failed child exit")
  await(function()
    for _, notification in ipairs(notifications) do
      if notification.message:find("exited with code 7", 1, true)
        and notification.message:find("Deliberate test receiver exit", 1, true) then return true end
    end
    return false
  end, "child diagnostic")
  local after_failure = updates()
  local failed_pid = after_failure[#after_failure].pid
  viewer.setup({ command = command })
  assert(viewer.start())
  await(function()
    local all = updates()
    return all[#all] and all[#all].pid ~= failed_pid and all[#all].message.text == "Pending at stop"
  end, "restart after child failure")
  viewer.stop()

  -- Commands coexist with the user's existing MarkdownPreview integration.
  assert(vim.fn.exists(":MdViewerStart") == 2)
  assert(vim.fn.exists(":MdViewerStop") == 2)
  assert(vim.fn.exists(":MdViewerToggle") == 2)
  assert(vim.fn.exists(":MarkdownPreview") == 0)
  local last = {}
  for _, record in ipairs(updates()) do
    assert(record.message.revision > (last[record.pid] or 0), "revision must increase within each process")
    last[record.pid] = record.message.revision
  end
  print("Neovim unsaved/Insert/completion, reload, switch, stop/restart, and failure checks passed.")
end

local ok, failure = xpcall(run, debug.traceback)
viewer.stop()
if not ok then
  io.stderr:write(failure .. "\n")
  vim.cmd("cquit 1")
end
