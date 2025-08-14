# app.py — Sudoku for Aiden (9x9, keyboard input, tablet-ready, sounds, timer, 3 strikes)
import streamlit as st
import random, time
from copy import deepcopy
from streamlit.components.v1 import html as st_html

# -------------------- Page setup --------------------
st.set_page_config(
    page_title="Sudoku for Aiden",
    page_icon="🧩",
    layout="wide",                     # 태블릿/와이드 화면에 유리
    initial_sidebar_state="auto",
)
st.title("🧩 Sudoku for Aiden")

# -------------------- Base solved grid --------------------
SOL9_BASE = [
  [1,3,8,9,6,7,5,4,2],
  [6,9,7,5,4,2,8,1,3],
  [5,4,2,1,3,8,9,6,7],
  [9,7,1,3,5,6,2,8,4],
  [2,8,5,4,7,9,1,3,6],
  [3,6,4,2,8,1,7,9,5],
  [4,2,3,8,9,5,6,7,1],
  [8,5,6,7,1,4,3,2,9],
  [7,1,9,6,2,3,4,5,8],
]

def new9_solution(seed=None):
    rnd = random.Random(seed)
    perm = list(range(1,10))
    rnd.shuffle(perm)
    sol = [[perm[v-1] for v in row] for row in SOL9_BASE]

    def swap_rows(a,b): sol[a], sol[b] = sol[b], sol[a]
    def swap_cols(a,b):
        for r in range(9):
            sol[r][a], sol[r][b] = sol[r][b], sol[r][a]

    # shuffle within bands/stacks
    for band in (0,3,6):
        rows = [band, band+1, band+2]; rnd.shuffle(rows)
        tmp = sol[band:band+3]
        for i in range(3): sol[band+i] = tmp[rows.index(band+i)]
    for stack in (0,3,6):
        cols = [stack, stack+1, stack+2]; rnd.shuffle(cols)
        tmp = [row[stack:stack+3] for row in sol]
        for i in range(3):
            for r in range(9):
                sol[r][stack+i] = tmp[r][cols.index(stack+i)]

    # swap bands
    bands = [0,3,6]; rnd.shuffle(bands)
    if bands != [0,3,6]:
        tmp = deepcopy(sol)
        for i,b in enumerate(bands):
            for k in range(3):
                sol[i*3+k] = tmp[b+k]
    # swap stacks
    stacks = [0,3,6]; rnd.shuffle(stacks)
    if stacks != [0,3,6]:
        tmp = deepcopy(sol)
        for r in range(9):
            for i,s in enumerate(stacks):
                for k in range(3):
                    sol[r][i*3+k] = tmp[r][s+k]
    return sol

def densify_from_solution(solution, target_givens=65, seed=None):
    """정답에서 target_givens 만큼 힌트를 공개(쉬운 난이도)."""
    rnd = random.Random(seed)
    puzzle = [[0]*9 for _ in range(9)]
    cells = [(r,c) for r in range(9) for c in range(9)]
    rnd.shuffle(cells)
    target = max(30, min(81, target_givens))
    filled = 0
    while filled < target and cells:
        r,c = cells.pop()
        puzzle[r][c] = solution[r][c]
        filled += 1
    return puzzle

def is_solved(board, sol):
    return all(board[r][c]==sol[r][c] for r in range(9) for c in range(9))

# -------------------- Sounds via WebAudio --------------------
def play_beep(freq=440, duration_ms=150, volume=0.2):
    st_html(f"""
    <script>
    (function(){{
      const ctx = new (window.AudioContext||window.webkitAudioContext)();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = {freq};
      g.gain.value = {volume};
      o.connect(g); g.connect(ctx.destination);
      o.start();
      setTimeout(()=>{{o.stop(); ctx.close();}}, {int(duration_ms)});
    }})();
    </script>
    """, height=0)

def play_success():
    # 짧은 멜로디: 도–미–솔
    st_html("""
    <script>
    (function(){
      const ctx = new (window.AudioContext||window.webkitAudioContext)();
      function tone(f,t){
        const o=ctx.createOscillator(), g=ctx.createGain();
        o.type='sine'; o.frequency.value=f; g.gain.value=0.15;
        o.connect(g); g.connect(ctx.destination); o.start(t); o.stop(t+0.18);
      }
      const now = ctx.currentTime;
      tone(523.25, now);        // C5
      tone(659.25, now+0.20);   // E5
      tone(783.99, now+0.40);   // G5
      setTimeout(()=>ctx.close(), 1000);
    })();
    </script>
    """, height=0)

def play_fail():
    # 낮은 버즈음
    st_html("""
    <script>
    (function(){
      const ctx = new (window.AudioContext||window.webkitAudioContext)();
      const o=ctx.createOscillator(), g=ctx.createGain();
      o.type='square'; o.frequency.value=180; g.gain.value=0.12;
      o.connect(g); g.connect(ctx.destination); o.start(); 
      setTimeout(()=>{o.stop(); ctx.close();}, 400);
    })();
    </script>
    """, height=0)

# -------------------- Session state --------------------
def new_game(seed=None, target_givens=65):
    sol = new9_solution(seed)
    board = densify_from_solution(sol, target_givens=target_givens, seed=seed)
    given = [[board[r][c]!=0 for c in range(9)] for r in range(9)]  # 행우선(정상)
    st.session_state.solution = sol
    st.session_state.board = board
    st.session_state.given = given
    st.session_state.mistakes = 0
    st.session_state.game_over = False
    st.session_state.last_feedback = ""
    st.session_state.start_time = time.time()
    st.session_state.end_time = None
    # 입력 필드 초기화
    for r in range(9):
        for c in range(9):
            k = f"cell-{r}-{c}"
            st.session_state.pop(k, None)

if "board" not in st.session_state:
    new_game(seed=42, target_givens=65)

# -------------------- Sidebar (controls + timer + scale) --------------------
with st.sidebar:
    seed = st.number_input("시드(seed)", min_value=0, value=42, step=1)
    target = st.slider("힌트(채워진 칸) 개수", 45, 75, 65, 1)
    ui_scale = st.slider("화면 배율(탭 최적화)", 0.9, 1.6, 1.2, 0.05)
    if st.button("🔄 새 게임"):
        new_game(seed=seed, target_givens=target)
        st.rerun()

    # 타이머 표시
    def fmt_secs(sec:int):
        m = sec // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}"

    if st.session_state.end_time:
        elapsed = int(st.session_state.end_time - st.session_state.start_time)
        st.success(f"⏱ 경과: {fmt_secs(elapsed)}")
    else:
        elapsed = int(time.time() - st.session_state.start_time)
        st.info(f"⏱ 경과: {fmt_secs(elapsed)}")
        st.caption("입력/버튼 등 상호작용 시 갱신됩니다.")

    st.markdown("---")
    st.write(f"❌ 실수: **{st.session_state.mistakes} / 3**")
    if st.session_state.game_over:
        st.error("게임 실패! 🔁 새 게임을 눌러 다시 시작하세요.")
    elif is_solved(st.session_state.board, st.session_state.solution):
        st.success("정답! 🎉 훌륭해요!")

# -------------------- Input handler --------------------
def handle_input(r, c, key):
    if st.session_state.game_over or st.session_state.end_time:
        return
    txt = st.session_state.get(key, "").strip()

    # empty → clear
    if txt == "":
        st.session_state.board[r][c] = 0
        return
    # only 1..9
    if not txt.isdigit() or not (1 <= int(txt) <= 9):
        st.session_state[key] = ""
        play_beep(freq=300, duration_ms=120)    # 잘못된 키 → 짧은 경고음
        return

    val = int(txt)
    # 보호: given 셀
    if st.session_state.given[r][c]:
        st.session_state[key] = str(st.session_state.board[r][c] or "")
        play_beep(freq=300, duration_ms=120)
        return

    # 정답 점검
    if val == st.session_state.solution[r][c]:
        st.session_state.board[r][c] = val
        st.session_state.last_feedback = "✔️ 정답!"
        # 퍼즐 완성되었는지 확인
        if is_solved(st.session_state.board, st.session_state.solution):
            st.session_state.end_time = time.time()
            play_success()
    else:
        st.session_state.mistakes += 1
        st.session_state.last_feedback = f"❌ 틀렸어요. 남은 기회: {max(0,3 - st.session_state.mistakes)}"
        st.session_state.board[r][c] = 0
        st.session_state[key] = ""
        # 소리
        if st.session_state.mistakes >= 3:
            st.session_state.game_over = True
            st.session_state.end_time = time.time()
            play_fail()
        else:
            play_beep(freq=260, duration_ms=160)

# -------------------- Grid render (keyboard input) --------------------
# 굵은 3×3 경계: 가로/세로 검은 바
CELL_W = 1.0
SEP_W = 0.12
BASE_HEIGHT = 46
ROW_INPUT_HEIGHT_PX = int(BASE_HEIGHT * ui_scale)

def vertical_bar(height_px=ROW_INPUT_HEIGHT_PX):
    st.markdown(
        f"<div style='width:{int(4*ui_scale)}px;height:{height_px}px;background:black;border-radius:{int(2*ui_scale)}px;margin:{int(4*ui_scale)}px auto;'></div>",
        unsafe_allow_html=True
    )

def horizontal_bar():
    st.markdown(
        f"<div style='width:100%;height:{int(4*ui_scale)}px;background:black;border-radius:{int(2*ui_scale)}px;margin:{int(6*ui_scale)}px 0;'></div>",
        unsafe_allow_html=True
    )

board = st.session_state.board
given = st.session_state.given
sol = st.session_state.solution

# 상단 굵은 테두리
horizontal_bar()
for r in range(9):
    cols = st.columns(
        [CELL_W, CELL_W, CELL_W, SEP_W, CELL_W, CELL_W, CELL_W, SEP_W, CELL_W, CELL_W, CELL_W],
        gap="small"
    )
    for c_vis in range(11):
        if c_vis in (3,7):
            with cols[c_vis]:
                vertical_bar()
            continue
        real_c = c_vis - (1 if c_vis>3 else 0) - (1 if c_vis>7 else 0)
        with cols[c_vis]:
            is_given = given[r][real_c]
            val = board[r][real_c]
            if is_given:
                st.markdown(
                    f"<div style='border:{int(2*ui_scale)}px solid #333;border-radius:{int(10*ui_scale)}px;"
                    f"padding:{int(6*ui_scale)}px 0;text-align:center;font-size:{int(20*ui_scale)}px;"
                    f"font-weight:700;background:#f6f6f6;height:{ROW_INPUT_HEIGHT_PX}px;'>{val}</div>",
                    unsafe_allow_html=True
                )
            else:
                key = f"cell-{r}-{real_c}"
                if key not in st.session_state:
                    st.session_state[key] = (str(val) if val else "")
                disabled = st.session_state.game_over or st.session_state.end_time is not None
                st.text_input(
                    " ",
                    key=key,
                    value=st.session_state[key],
                    max_chars=1,
                    disabled=disabled,
                    label_visibility="collapsed",
                    on_change=handle_input,
                    args=(r, real_c, key),
                    placeholder="",
                )
    if r in (2,5):
        horizontal_bar()
# 하단 굵은 테두리
horizontal_bar()

# 피드백 문구
if st.session_state.last_feedback:
    if st.session_state.game_over:
        st.error(st.session_state.last_feedback)
    elif st.session_state.end_time:
        st.success("정답! 🎉")
    else:
        st.info(st.session_state.last_feedback)
