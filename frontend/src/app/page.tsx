"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";

type PageState = "home" | "processing" | "result" | "settings";
type SettingsTab = "voice" | "library";

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

export default function Home() {
  const API_BASE = typeof window !== "undefined" && window.location.hostname !== "localhost" 
    ? `http://192.168.3.110:8000` 
    : "http://localhost:8000";
  
  const [page, setPage] = useState<PageState>("home");
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
        console.log("Fetched voices:", data.voices);
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
        console.log("Fetched libraries:", data.libraries);
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
      if (resultData?.audioUrl) {
        setIsSpeaking(true);
        if (audioRef.current) {
          audioRef.current.src = resultData.audioUrl;
          audioRef.current.currentTime = 0;
          audioRef.current.play();
          audioRef.current.onended = () => setIsSpeaking(false);
        }
      } else {
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
        const voiceConfig = ttsData.config || {};
        if ("speechSynthesis" in window) {
          speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(textToSpeak);
          utterance.rate = voiceConfig.speed || 0.8;
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

function SettingsPage({
  voices,
  selectedVoice,
  onSelectVoice,
  onBack,
  apiBase,
  wordLibraries,
  selectedLibrary,
  onSelectLibrary,
}: {
  voices: Voice[];
  selectedVoice: string;
  onSelectVoice: (voiceId: string) => void;
  onBack: () => void;
  apiBase: string;
  wordLibraries: WordLibrary[];
  selectedLibrary: string;
  onSelectLibrary: (libraryId: string) => void;
}) {
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
      // Stop any currently playing audio
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current.src = "";
      }
      if ("speechSynthesis" in window) {
        speechSynthesis.cancel();
      }
      
      setPlayingPreview(voiceId);
      console.log("Fetching preview for voice:", voiceId);
      
      const formData = new FormData();
      formData.append("voice_id", voiceId);
      
      const response = await fetch(`${apiBase}/api/tts/preview?t=${Date.now()}`, {
        method: "POST",
        body: formData,
      });
      
      const data = await response.json();
      console.log("Preview response:", data);
      
      if (data.audio_url) {
        // Create completely new audio element to force fresh playback
        const newAudio = new Audio();
        newAudio.src = data.audio_url;
        console.log("Playing audio:", data.audio_url);
        
        newAudio.onended = () => setPlayingPreview(null);
        newAudio.onerror = () => setPlayingPreview(null);
        
        // Update the ref and play
        previewAudioRef.current = newAudio;
        newAudio.play().catch(e => {
          console.error("Play error:", e);
          setPlayingPreview(null);
        });
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
          音色选择
        </button>
        <button
          onClick={() => setActiveTab("library")}
          className={`flex-1 py-2 px-4 rounded-full transition-all ${activeTab === "library" ? "bg-[var(--zizi-primary)] text-white" : "text-[var(--zizi-dark)]"}`}
        >
          字库选择
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
    </div>
  );
}
