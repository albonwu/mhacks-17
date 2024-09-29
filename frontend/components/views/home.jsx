import React, { useState, useEffect, useCallback } from "react";
import styles from "../../styles/home.module.css";
import CodeMirror from "@uiw/react-codemirror";
import { loadLanguage } from "@uiw/codemirror-extensions-langs";
import { tokyoNight } from "@uiw/codemirror-theme-tokyo-night";
import { EyeDropper } from "react-eyedrop";
import DOMPurify from "dompurify";
import { useDispatch } from "react-redux";
import Timer from "./Timer";

const BACKEND = "http://127.0.0.1:5000";

const Home = () => {
  const [css, setCss] = useState(`
    body {
    background: white
    }
            div {
              height: 100px;
              width: 100px;
              background: #00274C;
              color: #FFCB05
            }`);
  const [html, _] = useState("<div>hello</div>");

  function handleTimerExpire() {
    // todo: do this
  }
  const dispatch = useDispatch();

  function generatePreviewHtml() {
    return `<html><style>body { margin: 0; height: 300px; width: 300px; } ${css}</style>${DOMPurify.sanitize(
      html
    )}</html>`;
  }

  const [sessionId, setSessionId] = useState();

  async function handleStart() {
    const res = await fetch(`${BACKEND}/start_session`, { method: "POST" });
    const newSessionId = await res.text();
    console.log("newSessionId", newSessionId);
    setSessionId(newSessionId);
  }

  async function handleSubmit() {
    const res = await fetch(`${BACKEND}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json", // Set appropriate content type
      },
      body: JSON.stringify({
        puzzle_id: "test",
        html: generatePreviewHtml(),
      }),
    });
  }

  // for skip button
  const [isDisabled, setIsDisabled] = useState(true);
  const [timerKey, setTimerKey] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsDisabled(false);
    }, 5000); // in ms
    return () => clearTimeout(timer);
  }, [timerKey]);

  const handleCssEditorChange = useCallback((val, viewUpdate) => {
    setCss(val);
  });

  const handleSkip = () => {
    // tried to make the 5s cooldown reset....
    // setIsDisabled(true);
    // setTimerKey((prev) => prev + 1);
  };

  function handleEnd() {}

  const [pickedColor, setPickedColor] = useState({ rgb: "", hex: "" });
  const [eyedropOnce] = useState(true); // only 1 use of the eyedropper per button press
  const handleChangeColor = ({ rgb, hex }) => {
    setPickedColor({ rgb, hex });
    navigator.clipboard.writeText(hex);
  };

  return (
    <div className={styles.container}>
      <div>
        <div className={styles.colorContainer}>
          <EyeDropper
            onChange={handleChangeColor}
            cursorActive="crosshair"
            className={styles.eyedropperButton}
          >
            pick color
          </EyeDropper>
          <div style={{ display: "flex", gap: "1rem", width: "100%" }}>
            <div
              className={styles.colorDrop}
              style={{ backgroundColor: pickedColor.hex }}
            />
            <div>
              <p>{pickedColor.rgb}</p>
              <p>{pickedColor.hex}</p>
            </div>
          </div>
        </div>
        <div className={styles.previewContainer}>
          <img
            // src={`${BACKEND}/${sessionId}/target`}
            src="https://corsproxy.io/?https://placewaifu.com/image/300"
            alt="target"
            className={styles.targetImage}
          />
          <iframe
            className={styles.preview}
            srcDoc={generatePreviewHtml()}
          ></iframe>{" "}
        </div>
      </div>

      <div className={styles.editorContainer}>
        <div className={styles.buttonContainer}>
          <Timer onExpire={handleTimerExpire} length={3 * 60 * 1000} />
        </div>
        <CodeMirror
          className={styles.htmlEditor}
          value={html}
          theme={tokyoNight}
          maxHeight="200px"
          extensions={[loadLanguage("html")]}
          editable={false}
        />
        <div className={styles.cssEditor}>
          <CodeMirror
            value={css}
            height="100%"
            theme={tokyoNight}
            extensions={[loadLanguage("css")]}
            onChange={handleCssEditorChange}
          />
        </div>
        <div className={styles.buttonContainer}>
          {/* <button onClick={handleStart} className={styles.gameButton}>
            Start
          </button> */}
          <div className={styles.buttonGroup}>
            <button
              className={`${styles.gameButton} ${styles.gameButtonDanger}`}
              onClick={() => {
                handleEnd;
              }}
            >
              {"End game"}
            </button>
            <button
              className={styles.gameButton}
              disabled={isDisabled}
              onClick={() => {
                handleSkip;
              }}
            >
              {isDisabled ? "Wait..." : "Skip"}
            </button>
          </div>
          <button
            className={`${styles.gameButton} ${styles.gameButtonPrimary}`}
            onClick={handleSubmit}
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};

export default Home;
