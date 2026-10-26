import type React from 'react';
import styles from './CodeViewer.module.css';

/* ── Token factory ── */
const token = (cls: string) =>
  function Token({ t }: { t: string }) { return <span className={cls}>{t}</span>; };

const Cmt = token(styles.cmt);
const Dec = token(styles.dec);
const Kw  = token(styles.kw);
const Fn  = token(styles.fn);
const Ty  = token(styles.ty);
const Str = token(styles.str);
const Doc = token(styles.doc);
const Op  = token(styles.op);
const Va  = token(styles.va);

interface LineProps { n: number; children?: React.ReactNode }
const L = ({ n, children }: LineProps) => (
  <div className={styles.line}>
    <span className={styles.ln}>{String(n).padStart(2, ' ')}</span>
    <span className={styles.lc}>{children ?? ' '}</span>
  </div>
);

/* Indent helpers */
const I1 = ({ children }: { children?: React.ReactNode }) => (
  <><span className={styles.indent} />{children}</>
);
const I2 = ({ children }: { children?: React.ReactNode }) => (
  <><span className={styles.indent} /><span className={styles.indent} />{children}</>
);

export default function CodeViewer() {
  return (
    <div className={styles.panel}>
      {/* ── Header ── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.fileIcon}>⬡</span>
          <span className={styles.filename}>agents/chat/index.py</span>
        </div>
        <span className={styles.badge}>READ ONLY</span>
      </div>

      {/* ── Code body ── */}
      <div className={styles.body}>
        {/* CRT scanline overlay */}
        <div className={styles.scanline} aria-hidden />

        <div className={styles.code}>
          {/* ── Imports ── */}
          <L n={1}><Kw t="from " /><Va t="agents" /><Kw t=" import " /><Ty t="Agent" /><Op t=", " /><Ty t="Runner" /></L>
          <L n={2} />
          <L n={3}><Kw t="from " /><Va t=".._tools" /><Kw t=" import " /><Op t="(" /></L>
          <L n={4}><I1><Fn t="search_malls_nearby" /><Op t=", " /><Fn t="search_brand_in_mall" /><Op t="," /></I1></L>
          <L n={5}><I1><Fn t="get_distance" /><Op t=", " /><Fn t="check_brands_in_malls" /><Op t="," /></I1></L>
          <L n={6}><Op t=")" /></L>
          <L n={7} />

          {/* ── 1. 高德真实工具 ── */}
          <L n={8}><Cmt t="# 1. 高德地图真实工具：Key 只从环境变量读取" /></L>
          <L n={9}><Dec t="@function_tool" /></L>
          <L n={10}>
            <Kw t="def " /><Fn t="search_malls_nearby" /><Op t="(" />
            <Va t="location" /><Op t=": " /><Ty t="str" /><Op t=", " />
            <Va t="radius_m" /><Op t=": " /><Ty t="int" /><Op t=" = " /><Va t="3000" /><Op t=") -> " /><Ty t="str" /><Op t=":" />
          </L>
          <L n={11}><I1><Doc t='"""按 types=060100 检索周边商场，结果按距离升序。"""' /></I1></L>
          <L n={12} />
          <L n={13}><Dec t="@function_tool" /></L>
          <L n={14}>
            <Kw t="def " /><Fn t="search_brand_in_mall" /><Op t="(" />
            <Va t="mall" /><Op t=": " /><Ty t="str" /><Op t=", " /><Va t="brand" /><Op t=": " /><Ty t="str" /><Op t=") -> " /><Ty t="str" /><Op t=":" />
          </L>
          <L n={15}><I1><Doc t='"""核验商场内是否有该品牌门店，返回门店名与楼层。"""' /></I1></L>
          <L n={16} />
          <L n={17}><Dec t="@function_tool" /></L>
          <L n={18}>
            <Kw t="def " /><Fn t="get_distance" /><Op t="(" />
            <Va t="origin" /><Op t=": " /><Ty t="str" /><Op t=", " /><Va t="destination" /><Op t=": " /><Ty t="str" /><Op t=") -> " /><Ty t="str" /><Op t=":" />
          </L>
          <L n={19}><I1><Doc t='"""步行/驾车距离与耗时，接口不可用时退回直线距离。"""' /></I1></L>
          <L n={20} />
          <L n={21}><Dec t="@function_tool" /></L>
          <L n={22}>
            <Kw t="def " /><Fn t="check_brands_in_malls" /><Op t="(" />
            <Va t="location" /><Op t=": " /><Ty t="str" /><Op t=", " />
            <Va t="mall_names" /><Op t=": " /><Ty t="str" /><Op t=", " />
            <Va t="brands" /><Op t=": " /><Ty t="str" /><Op t=") -> " /><Ty t="str" /><Op t=":" />
          </L>
          <L n={23}><I1><Doc t='"""批量核验多商场 × 多品牌，按距离排序。"""' /></I1></L>
          <L n={24} />
          <L n={25}>
            <Va t="TOOLS" /><Op t=" = [" /><Fn t="search_malls_nearby" /><Op t=", " /><Fn t="search_brand_in_mall" /><Op t="," />
          </L>
          <L n={26}><I1><Fn t="get_distance" /><Op t=", " /><Fn t="check_brands_in_malls" /><Op t="]" /></I1></L>
          <L n={27} />

          {/* ── 2. Agent ── */}
          <L n={28}><Cmt t="# 2. Agent：出行决策助手" /></L>
          <L n={29}>
            <Va t="agent" /><Op t=" = " /><Ty t="Agent" /><Op t="(" />
          </L>
          <L n={30}>
            <I1><Va t="name" /><Op t="=" /><Str t='"出行决策助手"' /><Op t="," /></I1>
          </L>
          <L n={31}>
            <I1><Va t="instructions" /><Op t="=" /><Va t="INSTRUCTIONS" /><Op t="," /><Cmt t="  # 决策流程与硬性规则" /></I1>
          </L>
          <L n={32}>
            <I1><Va t="tools" /><Op t="=" /><Va t="TOOLS" /><Op t="," /></I1>
          </L>
          <L n={33}>
            <I1><Va t="model" /><Op t="=" /><Va t="llm_model" /><Op t="," /></I1>
          </L>
          <L n={34}>
            <Op t=")" />
          </L>
          <L n={35} />

          {/* ── 3. Handler ── */}
          <L n={36}>
            <Kw t="async def " /><Fn t="handler" /><Op t="(" /><Va t="context" /><Op t="):" />
          </L>
          <L n={37}>
            <I1><Va t="message" /><Op t=" = " /><Va t="context" /><Op t="." /><Va t="request" /><Op t="." /><Va t="body" /><Op t="." /><Fn t="get" /><Op t="(" /><Str t='"message"' /><Op t=", " /><Str t='""' /><Op t=")" /></I1>
          </L>
          <L n={38}>
            <I1><Va t="cid" /><Op t=" = " /><Va t="context" /><Op t="." /><Va t="conversation_id" /></I1>
          </L>
          <L n={39}>
            <I1><Va t="session" /><Op t=" = " /><Va t="context" /><Op t="." /><Va t="store" /><Op t="." /><Fn t="openai_session" /><Op t="(" /><Va t="cid" /><Op t=")" /></I1>
          </L>
          <L n={40} />
          <L n={41}>
            <I1><Cmt t="# 3. 流式输出，多轮记忆由 SDK session 自动注入" /></I1>
          </L>
          <L n={42}>
            <I1><Va t="result" /><Op t=" = " /><Ty t="Runner" /><Op t="." /><Fn t="run_streamed" /><Op t="(" /><Va t="agent" /><Op t=", " /><Va t="message" /><Op t=", " /><Va t="session" /><Op t=")" /></I1>
          </L>
          <L n={43}>
            <I1><Kw t="async for " /><Va t="event" /><Kw t=" in " /><Va t="result" /><Op t="." /><Fn t="stream_events" /><Op t="():" /></I1>
          </L>
          <L n={44}>
            <I2><Cmt t="# text_delta / tool_called → SSE 帧" /></I2>
          </L>
        </div>
      </div>

      {/* ── Footer tag ── */}
      <div className={styles.footer}>
        <span className={styles.footerDot} />
        <span>OpenAI Agents SDK · EdgeOne Makers</span>
      </div>
    </div>
  );
}
