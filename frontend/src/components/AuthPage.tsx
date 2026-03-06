"use client";

import { useState } from "react";

interface AuthPageProps {
  onLogin: (token: string, user: any) => void;
  onGuest: () => void;
  apiBase: string;
}

export default function AuthPage({ onLogin, onGuest, apiBase }: AuthPageProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validatePhone = (phone: string) => {
    return /^1\d{10}$/.test(phone);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validatePhone(phone)) {
      setError("请输入正确的手机号");
      return;
    }

    if (password.length < 6) {
      setError("密码至少6位");
      return;
    }

    if (!isLogin && password !== confirmPassword) {
      setError("两次密码不一致");
      return;
    }

    setLoading(true);

    try {
      const endpoint = isLogin ? "/api/auth/login" : "/api/auth/register";
      const response = await fetch(`${apiBase}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ phone, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || (isLogin ? "登录失败" : "注册失败"));
      }

      localStorage.setItem("zizi_token", data.access_token);
      localStorage.setItem("zizi_refresh_token", data.refresh_token);
      localStorage.setItem("zizi_user", JSON.stringify(data.user));

      onLogin(data.access_token, data.user);
    } catch (err: any) {
      setError(err.message || "网络错误");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50/50 via-white to-cyan-50/30 flex items-center justify-center p-6">
      {/* 浮动装饰元素 */}
      <div className="fixed top-20 left-10 w-20 h-20 bg-gradient-to-br from-rose-200/40 to-rose-300/40 rounded-full blur-2xl animate-pulse pointer-events-none" />
      <div className="fixed bottom-32 right-10 w-32 h-32 bg-gradient-to-br from-cyan-200/40 to-teal-300/40 rounded-full blur-2xl animate-pulse pointer-events-none" style={{ animationDelay: "1s" }} />

      {/* 主内容卡片 */}
      <div className="w-full max-w-sm">
        {/* Logo区域 */}
        <div className="text-center mb-12">
          {/* 吉祥物 */}
          <div className="relative inline-block mb-6">
            <div className="w-20 h-20 mx-auto relative">
              {/* 外圈光晕 */}
              <div className="absolute inset-0 bg-gradient-to-br from-rose-400 to-rose-500 rounded-full animate-ping opacity-10" style={{ animationDuration: "2s" }} />
              {/* 主体 */}
              <div className="absolute inset-0 bg-gradient-to-br from-rose-400 via-rose-500 to-rose-600 rounded-full shadow-xl flex items-center justify-center">
                <div className="flex gap-2">
                  <div className="w-3 h-4 bg-white rounded-full relative overflow-hidden">
                    <div className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-gray-800 rounded-full" />
                  </div>
                  <div className="w-3 h-4 bg-white rounded-full relative overflow-hidden">
                    <div className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-gray-800 rounded-full" />
                  </div>
                </div>
              </div>
              {/* 腮红 */}
              <div className="absolute bottom-3 left-2 w-3 h-1.5 bg-rose-300/50 rounded-full" />
              <div className="absolute bottom-3 right-2 w-3 h-1.5 bg-rose-300/50 rounded-full" />
            </div>
            {/* 小星星 */}
            <div className="absolute -top-1 -right-1 text-lg animate-bounce" style={{ animationDuration: "1.5s" }}>✨</div>
          </div>

          <h1 className="text-4xl font-light text-gray-900 tracking-tight mb-2">
            zizi
          </h1>
          <p className="text-sm text-gray-400 font-light tracking-widest">
            AI 识字伴侣
          </p>
        </div>

        {/* 表单卡片 */}
        <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-lg shadow-gray-200/50 p-8">
          {/* 错误提示 */}
          {error && (
            <div className="mb-6 py-3 px-4 bg-red-50 rounded-xl">
              <p className="text-sm text-red-500 text-center">{error}</p>
            </div>
          )}

          {/* 表单 */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* 手机号 */}
            <div>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="手机号"
                maxLength={11}
                className="w-full h-14 px-5 text-base text-gray-900 placeholder-gray-400 bg-gray-50 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-200 focus:bg-white transition-all"
              />
            </div>

            {/* 密码 */}
            <div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="密码"
                minLength={6}
                className="w-full h-14 px-5 text-base text-gray-900 placeholder-gray-400 bg-gray-50 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-200 focus:bg-white transition-all"
              />
            </div>

            {/* 确认密码 */}
            {!isLogin && (
              <div>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="确认密码"
                  minLength={6}
                  className="w-full h-14 px-5 text-base text-gray-900 placeholder-gray-400 bg-gray-50 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-200 focus:bg-white transition-all"
                />
              </div>
            )}

            {/* 提交按钮 */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full h-14 bg-rose-400 hover:bg-rose-500 text-white text-base font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    {isLogin ? "登录中" : "注册中"}
                  </span>
                ) : (
                  isLogin ? "登录" : "注册"
                )}
              </button>
            </div>
          </form>

          {/* 切换 */}
          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsLogin(!isLogin);
                setError(null);
                setConfirmPassword("");
              }}
              className="text-sm text-gray-400 hover:text-rose-400 transition-colors"
            >
              {isLogin ? "注册新账户" : "已有账户，去登录"}
            </button>
          </div>

          {/* 分隔线 */}
          <div className="my-8 flex items-center">
            <div className="flex-1 h-px bg-gray-100" />
            <span className="px-4 text-xs text-gray-300">或</span>
            <div className="flex-1 h-px bg-gray-100" />
          </div>

          {/* 游客模式 */}
          <button
            onClick={onGuest}
            className="w-full h-14 text-gray-500 hover:text-gray-700 hover:bg-gray-50 text-base font-medium rounded-xl transition-all"
          >
            暂不登录
          </button>
        </div>

        {/* 底部说明 */}
        <p className="mt-8 text-center text-xs text-gray-300">
          登录后可同步学习进度
        </p>
      </div>
    </div>
  );
}
