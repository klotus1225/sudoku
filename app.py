# app.py — Adult 9x9 Sudoku (easy) with keyboard input, bold 3x3 borders, and 3 strikes rule
import streamlit as st
import random
from copy import deepcopy

st.set_page_config(page_title="Sudoku — Adult Easy", page_icon="🧩", layout="centered")
st.title("🧩 Adult Sudoku (쉬운 버전)")

# ---- Base solved grid (we will shuffle to get new solutions) ----
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
    # number permutation
    perm = list(range(1,10))
    rnd.shuffle(perm)
    sol = [[perm[v-1] for v in row] for row in SOL9_BASE]

    # helper swappers
    def swap_rows(a,b):
        sol[a], sol[b] = sol[b], sol[a]
    def swap_cols(a,b):
        for r in range(9):
            sol[r][a], sol[r][b] = sol[r][b], sol[r][a]

    # shuffle within bands/stacks
    for band in (0,3,6):
        rows = [band, band+1, band+2]
        rnd.shuffle(rows)
        base = [band, band+1, band+2]
        for i in range(3):
            if rows[i] != base[i]:
                swap_rows(base[i], rows[i])
    for stack in (0,3,6):
        cols = [stack, stack+1, stack+2]
        rnd.shuffle(cols)
        base = [stack, stack+1, stack+2]
        for i in range(3):
            if cols[i] != base[i]:
                swap_cols(base[i], cols[i])

    # swap bands
    bands = [0,3,6]; rnd.shuffle(bands)
    if bands != [0,3,6]:
        tmp = deepcopy(sol)
        for i, b in enumerate(bands):
            for k in range(3):
                sol[i*3 + k] = tmp[b + k]

    # swap stacks
    stacks = [0,3,6]; rnd.shuffle(stacks)
    if stacks != [0,3,6]:
        tmp = deepcopy(sol)
        for r in range(9):
            for i, s in enumerate(stacks):
                for k in range(3):
                    sol[r][i*3 + k] = tmp[r][s + k]
    return sol

def densify_from_solution(solution, target_givens=60, seed=None):
    """Create an easy puzzle by revealing many cells from the solution."""
    rnd = random.Random(seed)
    puzzle = [[0]*9 for _ in range(9)]
    cells = [(r,c) for r in range(9) for c in range(9)]
    rnd.shuffle(cells)
    target = max(30, min(81, target_givens))
    while sum(1 for r in range(9) for c in range(9) if puzzle[r][c]!=0) < target and cells:
        r,c = cells.pop()
        puzzle[r][c] = solution[r][c]
    return puzzle

def is_solved(board, sol):
    return all(board[r][c]==sol[r][c] for r in range(9) for c in range(9))

# --- Session state init ---
def new_game(seed=None, target_givens=60):
    sol = new9_solution(seed)
    board = densify_from_solution(sol, target_givens=target_givens, seed=seed)
    given = [[board[r][c]!=0 for r in range(9)] for c in range(9)]
    st.session_state.solution = sol
    st.session_state.board = board
    st.session_state.given = given
    st.session_state.mistakes = 0
    st.session_state.game_over = False
    st.session_state.last_feedback = ""

if "board" not in st.session_state:
    new_game(seed=42, target_givens=65)

# ---- Sidebar controls ----
with st.sidebar:
    seed = st.number_input("시드(seed)", min_value=0, value=42, step=1)
    target = st.slider("힌트(채워진 칸) 개수", 45, 75, 65, 1)
    if st.button("🔄 새 게임"):
        new_game(seed=seed, target_givens=target)
        st.rerun()
    st.markdown("---")
    st.write(f"❌ 실수: **{st.session_state.mistakes} / 3**")
    if st.session_state.game_over:
        st.error("게임 실패! 🔁 새 게임을 눌러 다시 시작하세요.")
    elif is_solved(st.session_state.board, st.session_state.solution):
        st.success("정답! 🎉 훌륭해요!")

# ---- Input handler (called when a cell changes) ----
def handle_input(r, c, key):
    if st.session_state.game_over:
        return
    txt = st.session_state.get(key, "").strip()
    # empty input → clear
    if txt == "":
        st.session_state.board[r][c] = 0
        return
    # only allow 1..9
    if not txt.isdigit() or not (1 <= int(txt) <= 9):
        st.session_state[key] = ""  # clear invalid
        return
    val = int(txt)
    # given cells should be locked, but just in case:
    if st.session_state.given[c][r]:
        st.session_state[key] = str(st.session_state.board[r][c] or "")
        return

    # check against solution
    if val == st.session_state.solution[r][c]:
        st.session_state.board[r][c] = val
        st.session_state.last_feedback = "✔️ 정답!"
    else:
        # wrong attempt
        st.session_state.mistakes += 1
        st.session_state.last_feedback = f"❌ 틀렸어요. 남은 기회: {max(0,3 - st.session_state.mistakes)}"
        # clear the cell
        st.session_state.board[r][c] = 0
        st.session_state[key] = ""
        if st.session_state.mistakes >= 3:
            st.session_state.game_over = True

# ---- Grid render (keyboard input via text_input) ----
# Trick: build each row with 11 columns -> after col 2 and 5, insert a thin spacer column with a vertical black bar
CELL_W = 1.0
SEP_W = 0.12
ROW_INPUT_HEIGHT_PX = 46  # for vertical bar height

def vertical_bar(height_px=ROW_INPUT_HEIGHT_PX):
    st.markdown(
        f"<div style='width:4px;height:{height_px}px;background:black;border-radius:2px;margin:4px auto;'></div>",
        unsafe_allow_html=True
    )

def horizontal_bar():
    st.markdown("<div style='width:100%;height:4px;background:black;border-radius:2px;margin:6px 0;'></div>",
                unsafe_allow_html=True)

board = st.session_state.board
given = st.session_state.given
sol = st.session_state.solution

# top outer border
horizontal_bar()
for r in range(9):
    # make 11 columns: 3 cells, sep, 3 cells, sep, 3 cells
    cols = st.columns([CELL_W, CELL_W, CELL_W, SEP_W, CELL_W, CELL_W, CELL_W, SEP_W, CELL_W, CELL_W, CELL_W], gap="small")
    for c in range(11):
        # spacer bars at indices 3 and 7
        if c in (3,7):
            with cols[c]:
                vertical_bar()
            continue
        # map visual index to board col index
        real_c = c - (1 if c>3 else 0) - (1 if c>7 else 0)
        with cols[c]:
            is_given = given[real_c][r]
            val = board[r][real_c]
            # style for given cells: bold box with gray background
            if is_given:
                st.markdown(
                    f"<div style='border:2px solid #333;border-radius:10px;padding:6px 0;text-align:center;"
                    f"font-size:20px;font-weight:700;background:#f6f6f6;height:{ROW_INPUT_HEIGHT_PX}px;'>"
                    f"{val}</div>", unsafe_allow_html=True
                )
            else:
                key = f"cell-{r}-{real_c}"
                # prefill session value from board for consistent reruns
                if key not in st.session_state:
                    st.session_state[key] = (str(val) if val else "")
                disabled = st.session_state.game_over or is_solved(board, sol)
                st.text_input(
                    " ",  # label hidden
                    key=key,
                    value=st.session_state[key],
                    max_chars=1,
                    disabled=disabled,
                    label_visibility="collapsed",
                    on_change=handle_input,
                    args=(r, real_c, key),
                    placeholder="",
                )
    # horizontal bold line after row 2 and 5
    if r in (2,5):
        horizontal_bar()

# bottom outer border
horizontal_bar()

# feedback area
if st.session_state.last_feedback:
    if st.session_state.game_over:
        st.error(st.session_state.last_feedback)
    else:
        # soft info unless solved
        if is_solved(board, sol):
            st.success("정답! 🎉")
        else:
            st.info(st.session_state.last_feedback)

# action buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("✅ 전체 채점"):
        if is_solved(board, sol):
            st.success("정답! 훌륭해요 🎉")
        else:
            st.warning("아직 완성되지 않았어요. 계속 해보세요!")
with col2:
    if st.button("🧹 비어있는 칸 지우기", disabled=st.session_state.game_over):
        for rr in range(9):
            for cc in range(9):
                if not given[cc][rr]:
                    board[rr][cc] = 0
                    kk = f"cell-{rr}-{cc}"
                    if kk in st.session_state:
                        st.session_state[kk] = ""
        st.session_state.last_feedback = "빈칸을 모두 지웠어요."
        st.rerun()
