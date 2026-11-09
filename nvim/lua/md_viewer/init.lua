local M = {}

local uv = vim.uv or vim.loop
local config = { command = { "md-viewer" }, debounce_ms = 60, theme = "moonlit" }
local active
local attached = {}
local themes = { moonlit = true, graphite = true, paper = true }
local MAX_TEXT_BYTES = 1024 * 1024
local MAX_FRAME_BYTES = 2 * 1024 * 1024

local function notify(message, level)
  vim.schedule(function()
    vim.notify(message, level or vim.log.levels.ERROR, { title = "md_viewer" })
  end)
end

local function close_timer(session)
  if session.timer and not session.timer:is_closing() then
    session.timer:stop()
    session.timer:close()
  end
  session.timer = nil
end

local function markdown_buffer(buf)
  return vim.api.nvim_buf_is_valid(buf)
    and vim.api.nvim_buf_is_loaded(buf)
    and vim.bo[buf].buftype == ""
    and vim.bo[buf].filetype == "markdown"
end

local function send_snapshot(session)
  if active ~= session or not markdown_buffer(session.buffer) then
    return
  end
  local buf = session.buffer
  local text = table.concat(vim.api.nvim_buf_get_lines(buf, 0, -1, false), "\n")
  if #text > MAX_TEXT_BYTES then
    if not session.oversized then
      notify("This note exceeds the 1 MiB preview limit; showing the previous preview.", vim.log.levels.WARN)
    end
    session.oversized = true
    return
  end
  local name = vim.api.nvim_buf_get_name(buf)
  local snapshot = {
    version = 1,
    type = "update",
    revision = session.revision + 1,
    name = name ~= "" and name or "[No Name]",
    text = text,
    modified = vim.bo[buf].modified,
  }
  local ok, encoded = pcall(vim.json.encode, snapshot)
  if not ok then
    notify("Could not encode the current note: " .. tostring(encoded))
    return
  end
  if #encoded + 1 > MAX_FRAME_BYTES then
    if not session.oversized then
      notify("This note exceeds the 2 MiB encoded preview limit; showing the previous preview.", vim.log.levels.WARN)
    end
    session.oversized = true
    return
  end
  session.oversized = false
  local sent, result = pcall(vim.fn.chansend, session.job, encoded .. "\n")
  if not sent or result == 0 then
    notify("Preview connection closed. Run :MdViewerStart to reopen it.")
    M.stop()
    return
  end
  session.revision = snapshot.revision
end

local function queue_snapshot(session, immediate)
  if active ~= session or not session.timer then
    return
  end
  session.generation = session.generation + 1
  local generation = session.generation
  local buffer = session.buffer
  session.timer:stop()
  session.timer:start(immediate and 0 or config.debounce_ms, 0, vim.schedule_wrap(function()
    if active == session and session.generation == generation and session.buffer == buffer then
      send_snapshot(session)
    end
  end))
end

local function attach(buf)
  if attached[buf] then
    return true
  end
  local token = {}
  attached[buf] = token
  local function changed()
    if not active then
      if attached[buf] == token then attached[buf] = nil end
      return true
    end
    if active.buffer == buf then queue_snapshot(active, false) end
  end
  local ok = vim.api.nvim_buf_attach(buf, false, {
    on_lines = changed,
    on_reload = changed,
    on_changedtick = changed,
    on_detach = function()
      if attached[buf] == token then attached[buf] = nil end
      local session = active
      if session and session.buffer == buf then
        -- Buffer unload/deletion may happen while Neovim is choosing its next
        -- current buffer. BufEnter will attach the replacement if it is Markdown.
        session.generation = session.generation + 1
        if session.timer then session.timer:stop() end
      end
    end,
  })
  if not ok then attached[buf] = nil end
  return ok
end

local function follow(buf)
  if not active or not markdown_buffer(buf) then return end
  if not attach(buf) then
    notify("Could not attach to this Markdown buffer.")
    return
  end
  active.buffer = buf
  queue_snapshot(active, true)
end

function M.is_running()
  return active ~= nil
end

function M.stop()
  local session = active
  if not session then return end
  active = nil
  session.generation = session.generation + 1
  close_timer(session)
  -- Closing stdin asks the viewer to exit; jobstop also closes a viewer that is
  -- unresponsive. Both operate only on the process started by this session.
  pcall(vim.fn.chanclose, session.job, "stdin")
  pcall(vim.fn.jobstop, session.job)
end

function M.start()
  local buf = vim.api.nvim_get_current_buf()
  if not markdown_buffer(buf) then
    notify("Select a Markdown buffer first (:setfiletype markdown for an unnamed note).", vim.log.levels.WARN)
    return false
  end
  if active then
    follow(buf)
    return true
  end
  local argv = vim.deepcopy(config.command)
  vim.list_extend(argv, { "--stdin", "--theme", config.theme })
  local session = { buffer = buf, revision = 0, generation = 0, stderr = "" }
  local ok, job = pcall(vim.fn.jobstart, argv, {
    stdin = "pipe",
    on_stderr = function(_, data)
      -- Keep a bounded diagnostic tail, not the note contents.
      session.stderr = (session.stderr .. table.concat(data, "\n")):sub(-4096)
    end,
    on_exit = function(_, code)
      if active ~= session then return end
      active = nil
      close_timer(session)
      if code ~= 0 then
        local details = session.stderr:gsub("%s+$", "")
        notify("Preview exited with code " .. code .. (details ~= "" and (": " .. details) or ""))
      end
    end,
  })
  if not ok or job <= 0 then
    notify("Could not start md-viewer. Check setup.command and build the executable. " .. tostring(job))
    return false
  end
  session.job = job
  session.timer = uv.new_timer()
  active = session
  follow(buf)
  return true
end

function M.toggle()
  if active then M.stop() else M.start() end
end

function M.setup(options)
  options = options or {}
  local next_config = vim.tbl_deep_extend("force", {}, config, options)
  if type(next_config.command) == "string" then next_config.command = { next_config.command } end
  assert(type(next_config.command) == "table" and #next_config.command > 0, "md_viewer: command must be a nonempty argv list")
  for _, argument in ipairs(next_config.command) do
    assert(type(argument) == "string" and argument ~= "", "md_viewer: command arguments must be nonempty strings")
  end
  assert(type(next_config.debounce_ms) == "number" and next_config.debounce_ms >= 0
    and next_config.debounce_ms <= 1000 and next_config.debounce_ms % 1 == 0,
    "md_viewer: debounce_ms must be an integer between 0 and 1000")
  assert(themes[next_config.theme], "md_viewer: theme must be moonlit, graphite, or paper")
  M.stop()
  config = next_config
  local group = vim.api.nvim_create_augroup("MdViewer", { clear = true })
  vim.api.nvim_create_autocmd("BufEnter", { group = group, callback = function(args) follow(args.buf) end })
  vim.api.nvim_create_autocmd({ "BufWritePost", "BufFilePost", "BufModifiedSet" }, {
    group = group,
    callback = function(args)
      if active and active.buffer == args.buf then queue_snapshot(active, true) end
    end,
  })
  vim.api.nvim_create_autocmd("VimLeavePre", { group = group, callback = M.stop })
  vim.api.nvim_create_user_command("MdViewerStart", M.start, { desc = "Open live Markdown preview", force = true })
  vim.api.nvim_create_user_command("MdViewerStop", M.stop, { desc = "Close live Markdown preview", force = true })
  vim.api.nvim_create_user_command("MdViewerToggle", M.toggle, { desc = "Toggle live Markdown preview", force = true })
end

return M
