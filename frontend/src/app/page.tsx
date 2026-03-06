"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import AuthPage from "@/components/AuthPage";

type PageState = "auth" | "home" | "processing" | "result" | "settings";
type SettingsTab = "voice" | "library" | "account";

interface Voice {
  id: string;
  name: string;
  description: string;
  language: string;
  style: string;
  speed: number;
}

interface WordLibrary {
  id: string;
  name: string;
  description: string;
  word_count: number;
}

interface ResultData {
  imageUrl: string;
  character: string;
  story: string;
  audioUrl?: string;
  charAudioUrl?: string;
}

interface User {
  id: number;
  phone: string;
  nickname?: string;
}

export default function Home() {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // 认证状态
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  // 页面状态
  const [page, setPage] = useState<PageState>("auth");
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [resultData, setResultData] = useState<ResultData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("serena");
  const [wordLibraries, setWordLibraries] = useState<WordLibrary[]>([]);
  const [selectedLibrary, setSelectedLibrary] = useState<string>("infant");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // 检查自动登录
  useEffect(() => {
    const checkAuth = async () => {
      const savedToken = localStorage.getItem("zizi_token");
      const savedUser = localStorage.getItem("zizi_user");

      if (savedToken && savedUser) {
        try {
          const response = await fetch(`${API_BASE}/api/user/profile`, {
            headers: { Authorization: `Bearer ${savedToken}` },
          });

          if (response.ok) {
            setToken(savedToken);
            setUser(JSON.parse(savedUser));
            setIsAuthenticated(true);
            setPage("home");
          } else {
            const refreshToken = localStorage.getItem("zizi_refresh_token");
            if (refreshToken) {
              const refreshResponse = await fetch(`${API_BASE}/api/auth/refresh`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refreshToken }),
              });

              if (refreshResponse.ok) {
                const data = await refreshResponse.json();
                localStorage.setItem("zizi_token", data.access_token);
                setToken(data.access_token);
                setUser(JSON.parse(savedUser));
                setIsAuthenticated(true);
                setPage("home");
              } else {
                clearAuth();
              }
            } else {
              clearAuth();
            }
          }
        } catch (e) {
          console.error("Auth check failed:", e);
          clearAuth();
        }
      } else {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, [API_BASE]);

  const clearAuth = () => {
    localStorage.removeItem("zizi_token");
    localStorage.removeItem("zizi_refresh_token");
    localStorage.removeItem("zizi_user");
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const handleLogin = (newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    setIsAuthenticated(true);
    setPage("home");
  };

  const handleGuest = () => {
    setIsAuthenticated(false);
    setPage("home");
  };

  const handleLogout = () => {
    clearAuth();
    setPage("auth");
  };

  useEffect(() => {
    return () => {
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
      }
    };
  }, []);

  useEffect(() => {
    const savedVoice = localStorage.getItem("zizi_voice");
    if (savedVoice) {
      setSelectedVoice(savedVoice);
    }
  }, []);

  useEffect(() => {
    const savedLibrary = localStorage.getItem("zizi_library");
    if (savedLibrary) {
      setSelectedLibrary(savedLibrary);
    }
  }, []);

  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/voices?t=${Date.now()}`);
        const data = await res.json();
        setVoices(data.voices || []);
      } catch (e) {
        console.error("Failed to fetch voices:", e);
        setVoices([
          { id: "browser", name: "浏览器语音", description: "使用浏览器内置语音", language: "zh-CN", style: "default", speed: 0.8 },
        ]);
      }
    };
    fetchVoices();
  }, [API_BASE]);

  useEffect(() => {
    const fetchWordLibraries = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/word-libraries?t=${Date.now()}`);
        const data = await res.json();
        setWordLibraries(data.libraries || []);
      } catch (e) {
        console.error("Failed to fetch word libraries:", e);
        setWordLibraries([
          { id: "infant", name: "幼儿组", description: "100字", word_count: 100 },
        ]);
      }
    };
    fetchWordLibraries();
  }, [API_BASE]);

  useEffect(() => {
    if (page !== "result") {
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
      }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setIsSpeaking(false);
    }
  }, [page]);

  const handleCapture = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      const imageData = event.target?.result as string;
      setCapturedImage(imageData);
      setPage("processing");
      setErrorMessage(null);

      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("word_library", selectedLibrary);
        formData.append("voice_id", selectedVoice);
        if (token) {
          formData.append("authorization", `Bearer ${token}`);
        }

        const response = await fetch(`${API_BASE}/api/process`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error("识别失败了");
        }

        const data = await response.json();
        setResultData({
          imageUrl: imageData,
          character: data.target_char,
          story: data.story_text,
          audioUrl: data.audio_url,
          charAudioUrl: data.char_audio_url,
        });
        setPage("result");
      } catch (error) {
        console.error("Error:", error);
        setErrorMessage("哎呀，zizi看不清这个东西，让我们再试一次吧！");
        setTimeout(() => {
          setPage("home");
          setCapturedImage(null);
        }, 2000);
      }
    };
    reader.readAsDataURL(file);
  };

  const playStory = async () => {
    if (isSpeaking) {
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
      }
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setIsSpeaking(false);
      return;
    }

    const textToSpeak = resultData?.story || "";

    if (resultData?.audioUrl) {
      setIsSpeaking(true);
      if (audioRef.current) {
        audioRef.current.src = resultData.audioUrl;
        audioRef.current.currentTime = 0;
        audioRef.current.play();
        audioRef.current.onended = () => setIsSpeaking(false);
      }
      return;
    }

    if (selectedVoice === "browser" || !textToSpeak) {
      setIsSpeaking(true);
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(resultData?.story || "");
        utterance.rate = 0.8;
        utterance.pitch = 1.2;
        utterance.onend = () => setIsSpeaking(false);
        speechSynthesis.speak(utterance);
      } else {
        setIsSpeaking(false);
      }
      return;
    }

    try {
      setIsSpeaking(true);
      const formData = new FormData();
      formData.append("text", textToSpeak);
      formData.append("voice_id", selectedVoice);

      const ttsResponse = await fetch(`${API_BASE}/api/tts`, {
        method: "POST",
        body: formData,
      });

      const ttsData = await ttsResponse.json();

      if (!ttsData.use_browser && ttsData.audio_url) {
        if (audioRef.current) {
          audioRef.current.src = ttsData.audio_url;
          audioRef.current.currentTime = 0;
          audioRef.current.play();
          audioRef.current.onended = () => setIsSpeaking(false);
        }
      } else {
        if ("speechSynthesis" in window) {
          speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(textToSpeak);
          utterance.rate = 0.8;
          utterance.pitch = 1.2;
          utterance.onend = () => setIsSpeaking(false);
          speechSynthesis.speak(utterance);
        } else {
          setIsSpeaking(false);
        }
      }
    } catch (e) {
      console.error("TTS error:", e);
      setIsSpeaking(false);
    }
  };

  const replayCharacter = () => {
    if (resultData?.charAudioUrl) {
      if (audioRef.current) {
        audioRef.current.src = resultData.charAudioUrl;
        audioRef.current.currentTime = 0;
        audioRef.current.play();
      }
    } else if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(resultData?.character || "");
      utterance.rate = 0.6;
      utterance.pitch = 1.3;
      utterance.onend = () => {};
      speechSynthesis.speak(utterance);
    }
  };

  const reset = () => {
    if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setPage("home");
    setCapturedImage(null);
    setResultData(null);
    setIsPlaying(false);
    setIsSpeaking(false);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // 认证页面
  if (page === "auth" && isAuthenticated === false) {
    return (
      <AuthPage
        onLogin={handleLogin}
        onGuest={handleGuest}
        apiBase={API_BASE}
      />
    );
  }

  // 加载中
  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[var(--zizi-secondary)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* 登录状态指示器 */}
      {isAuthenticated && user && (
        <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 bg-white rounded-full shadow-md">
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[var(--zizi-primary)] to-[var(--zizi-secondary)] flex items-center justify-center text-white text-xs font-bold">
            {user.phone.slice(-2)}
          </div>
          <span className="text-sm text-gray-600">已登录</span>
        </div>
      )}

      {page === "home" && (
        <HomePage
          onCapture={handleCapture}
          errorMessage={errorMessage}
          onOpenSettings={() => setPage("settings")}
        />
      )}

      {page === "settings" && (
        <SettingsPage
          voices={voices}
          selectedVoice={selectedVoice}
          onSelectVoice={(voiceId) => {
            setSelectedVoice(voiceId);
            localStorage.setItem("zizi_voice", voiceId);
          }}
          onBack={() => setPage("home")}
          apiBase={API_BASE}
          wordLibraries={wordLibraries}
          selectedLibrary={selectedLibrary}
          onSelectLibrary={(libraryId) => {
            setSelectedLibrary(libraryId);
            localStorage.setItem("zizi_library", libraryId);
          }}
          isAuthenticated={isAuthenticated || false}
          user={user}
          onLogout={handleLogout}
          onLoginClick={() => setPage("auth")}
        />
      )}

      {page === "processing" && (
        <ProcessingPage imageUrl={capturedImage} onReset={reset} />
      )}

      {page === "result" && resultData && (
        <ResultPage
          resultData={resultData}
          isSpeaking={isSpeaking}
          onPlayStory={playStory}
          onReplayCharacter={replayCharacter}
          onReset={reset}
        />
      )}

      <audio ref={audioRef} />
    </div>
  );
}

function HomePage({
  onCapture,
  errorMessage,
  onOpenSettings,
}: {
  onCapture: () => void;
  errorMessage: string | null;
  onOpenSettings: () => void;
}) {
  const [showIntro, setShowIntro] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowIntro(true), 300);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex flex-col items-center gap-8">
      <button
        onClick={onOpenSettings}
        className="absolute top-4 right-4 p-3 rounded-full bg-white shadow-lg"
        style={{ color: "var(--zizi-dark)" }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      <div
        className={`transition-all duration-700 ${
          showIntro ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
        }`}
      >
        <h1 className="text-4xl font-bold text-center mb-2" style={{ color: "var(--zizi-primary)" }}>
          zizi
        </h1>
        <p className="text-lg text-center" style={{ color: "var(--zizi-dark)" }}>
          AI识字伴侣
        </p>
      </div>

      {errorMessage && (
        <div className="animate-bounce-in speech-bubble text-center">
          <p style={{ color: "var(--zizi-primary)" }}>{errorMessage}</p>
        </div>
      )}

      <button
        onClick={onCapture}
        className={`camera-button animate-breathe ${showIntro ? "animate-bounce-in" : "opacity-0"}`}
        style={{ animationDelay: "0.3s" }}
      >
        <div className="camera-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--zizi-primary)"
            strokeWidth="2"
            className="w-10 h-10"
          >
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
            <circle cx="12" cy="13" r="4" />
          </svg>
        </div>
      </button>

      <p
        className={`text-center text-lg transition-all duration-500 ${
          showIntro ? "opacity-100" : "opacity-0"
        }`}
        style={{ animationDelay: "0.6s" }}
      >
        点一下大眼睛<br />带zizi去看看你的玩具吧！
      </p>
    </div>
  );
}

function ProcessingPage({ imageUrl, onReset }: { imageUrl: string | null; onReset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-8">
      <button
        onClick={onReset}
        className="absolute top-4 left-4 p-3 rounded-full bg-white shadow-lg"
        style={{ color: "var(--zizi-dark)" }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <div className="text-3xl font-bold animate-float" style={{ color: "var(--zizi-primary)" }}>
        zizi正在吃掉这张照片...
      </div>

      <div className="relative">
        {imageUrl && (
          <Image
            src={imageUrl}
            alt="Captured"
            width={200}
            height={200}
            className="rounded-full animate-chew"
            style={{ objectFit: "cover" }}
          />
        )}
        <div className="absolute -bottom-4 -right-4 text-6xl animate-chew">
          😋
        </div>
      </div>

      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-4 h-4 rounded-full"
            style={{
              backgroundColor: "var(--zizi-secondary)",
              animation: `bounce 0.6s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function ResultPage({
  resultData,
  isSpeaking,
  onPlayStory,
  onReplayCharacter,
  onReset,
}: {
  resultData: ResultData;
  isSpeaking: boolean;
  onPlayStory: () => void;
  onReplayCharacter: () => void;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-col items-center gap-4 w-full max-w-md pb-6">
      <button
        onClick={onReset}
        className="absolute top-4 left-4 p-3 rounded-full bg-white shadow-lg"
        style={{ color: "var(--zizi-dark)" }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <div className="photo-frame animate-glow-pulse -mt-8">
        <Image
          src={resultData.imageUrl}
          alt="Captured"
          width={240}
          height={240}
          className="w-60 h-60"
          style={{ objectFit: "cover" }}
        />
      </div>

      <div
        className="character-display animate-character-reveal cursor-pointer hover:scale-110 transition-transform text-7xl"
        style={{ animationDelay: "0.2s" }}
        onClick={onReplayCharacter}
      >
        {resultData.character}
      </div>

      <div
        className={`speech-bubble w-full animate-speak-bubble cursor-pointer hover:scale-105 transition-transform text-base mt-2 ${isSpeaking ? "animate-pulse" : ""}`}
        style={{ animationDelay: "0.4s" }}
        onClick={onPlayStory}
      >
        <p className="leading-relaxed">{resultData.story}</p>
      </div>

      <div className="flex gap-4">
        <button
          onClick={onPlayStory}
          className="action-button primary-button"
        >
          {isSpeaking ? "⏹ 停止播放" : "▶ 听zizi讲故事"}
        </button>
        <button onClick={onReset} className="action-button secondary-button">
          再玩一次
        </button>
      </div>
    </div>
  );
}

interface SettingsPageProps {
  voices: Voice[];
  selectedVoice: string;
  onSelectVoice: (voiceId: string) => void;
  onBack: () => void;
  apiBase: string;
  wordLibraries: WordLibrary[];
  selectedLibrary: string;
  onSelectLibrary: (libraryId: string) => void;
  isAuthenticated: boolean;
  user: User | null;
  onLogout: () => void;
  onLoginClick: () => void;
}

function SettingsPage({
  voices,
  selectedVoice,
  onSelectVoice,
  onBack,
  apiBase,
  wordLibraries,
  selectedLibrary,
  onSelectLibrary,
  isAuthenticated,
  user,
  onLogout,
  onLoginClick,
}: SettingsPageProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("voice");
  const [playingPreview, setPlayingPreview] = useState<string | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement>(null);

  const handleVoiceClick = async (voiceId: string) => {
    if (playingPreview) {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current.currentTime = 0;
      }
      setPlayingPreview(null);
      return;
    }

    onSelectVoice(voiceId);

    if (voiceId === "browser") {
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance("你好啊");
        utterance.rate = 0.8;
        utterance.pitch = 1.2;
        utterance.onend = () => setPlayingPreview(null);
        setPlayingPreview(voiceId);
        speechSynthesis.speak(utterance);
      }
      return;
    }

    try {
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current.src = "";
      }
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
      }

      setPlayingPreview(voiceId);

      const formData = new FormData();
      formData.append("voice_id", voiceId);

      const response = await fetch(`${apiBase}/api/tts/preview?t=${Date.now()}`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.audio_url) {
        const newAudio = new Audio();
        newAudio.src = data.audio_url;
        newAudio.onended = () => setPlayingPreview(null);
        newAudio.onerror = () => setPlayingPreview(null);
        previewAudioRef.current = newAudio;
        newAudio.play().catch(() => setPlayingPreview(null));
      } else if (data.use_browser) {
        if ("speechSynthesis" in window) {
          speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance("你好啊");
          utterance.rate = 0.8;
          utterance.pitch = 1.2;
          utterance.onend = () => setPlayingPreview(null);
          speechSynthesis.speak(utterance);
        }
      }
    } catch (e) {
      console.error("Preview error:", e);
      setPlayingPreview(null);
    }
  };

  return (
    <div className="flex flex-col items-center gap-6 w-full max-w-md">
      <audio ref={previewAudioRef} />

      <button
        onClick={onBack}
        className="absolute top-4 left-4 p-3 rounded-full bg-white shadow-lg"
        style={{ color: "var(--zizi-dark)" }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      <h2 className="text-2xl font-bold mt-8" style={{ color: "var(--zizi-primary)" }}>
        设置
      </h2>

      <div className="flex w-full rounded-full bg-white p-1 shadow-md">
        <button
          onClick={() => setActiveTab("voice")}
          className={`flex-1 py-2 px-4 rounded-full transition-all ${activeTab === "voice" ? "bg-[var(--zizi-primary)] text-white" : "text-[var(--zizi-dark)]"}`}
        >
          音色
        </button>
        <button
          onClick={() => setActiveTab("library")}
          className={`flex-1 py-2 px-4 rounded-full transition-all ${activeTab === "library" ? "bg-[var(--zizi-primary)] text-white" : "text-[var(--zizi-dark)]"}`}
        >
          字库
        </button>
        <button
          onClick={() => setActiveTab("account")}
          className={`flex-1 py-2 px-4 rounded-full transition-all ${activeTab === "account" ? "bg-[var(--zizi-primary)] text-white" : "text-[var(--zizi-dark)]"}`}
        >
          账户
        </button>
      </div>

      {activeTab === "voice" && (
        <div className="w-full flex flex-col gap-3">
          {voices.map((voice) => (
            <button
              key={voice.id}
              onClick={() => handleVoiceClick(voice.id)}
              className={`voice-item ${selectedVoice === voice.id ? "selected" : ""} ${playingPreview === voice.id ? "playing" : ""}`}
            >
              <div className="flex flex-col items-start">
                <span className="font-bold text-lg" style={{ color: "var(--zizi-dark)" }}>
                  {voice.name}
                </span>
                <span className="text-sm" style={{ color: "#888" }}>
                  {voice.description}
                </span>
              </div>
              {selectedVoice === voice.id && (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="var(--zizi-secondary)" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
              {playingPreview === voice.id && (
                <span className="text-sm animate-pulse" style={{ color: "var(--zizi-secondary)" }}>
                  播放中...
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {activeTab === "library" && (
        <div className="w-full flex flex-col gap-3">
          {wordLibraries.map((library) => (
            <button
              key={library.id}
              onClick={() => onSelectLibrary(library.id)}
              className={`voice-item ${selectedLibrary === library.id ? "selected" : ""}`}
            >
              <div className="flex flex-col items-start">
                <span className="font-bold text-lg" style={{ color: "var(--zizi-dark)" }}>
                  {library.name}
                </span>
                <span className="text-sm" style={{ color: "#888" }}>
                  {library.description}
                </span>
              </div>
              {selectedLibrary === library.id && (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="var(--zizi-secondary)" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}

      {activeTab === "account" && (
        <div className="w-full flex flex-col gap-4">
          {isAuthenticated && user ? (
            <>
              <div className="bg-white rounded-2xl p-6 shadow-md">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--zizi-primary)] to-[var(--zizi-secondary)] flex items-center justify-center text-white text-2xl font-bold">
                    {user.phone.slice(-2)}
                  </div>
                  <div>
                    <p className="font-bold text-lg" style={{ color: "var(--zizi-dark)" }}>
                      已登录
                    </p>
                    <p className="text-sm text-gray-500">
                      {user.phone.slice(0, 3)}****{user.phone.slice(-4)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl p-4 shadow-md">
                <p className="text-sm text-gray-600 mb-2">账户功能</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm">学习进度同步</span>
                    <span className="text-sm text-green-500">已开启</span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm">跨设备使用</span>
                    <span className="text-sm text-green-500">已开启</span>
                  </div>
                </div>
              </div>

              <button
                onClick={onLogout}
                className="w-full py-4 rounded-xl font-bold text-white transition-all"
                style={{
                  background: "linear-gradient(135deg, #ff6b6b 0%, #ff8e8e 100%)",
                }}
              >
                退出登录
              </button>
            </>
          ) : (
            <>
              <div className="bg-white rounded-2xl p-6 shadow-md text-center">
                <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center mx-auto mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <p className="font-bold text-lg mb-2" style={{ color: "var(--zizi-dark)" }}>
                  当前为游客模式
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  登录后可以同步学习记录，换设备不丢失进度
                </p>
                <button
                  onClick={onLoginClick}
                  className="w-full py-3 rounded-xl font-bold text-white transition-all"
                  style={{
                    background: "linear-gradient(135deg, var(--zizi-secondary) 0%, #6EE7DE 100%)",
                  }}
                >
                  立即登录
                </button>
              </div>

              <div className="bg-yellow-50 rounded-2xl p-4 border border-yellow-200">
                <p className="text-sm text-yellow-700">
                  <span className="font-bold">提示：</span>
                  游客模式下的学习记录仅保存在当前设备，清除浏览器数据会丢失。
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
