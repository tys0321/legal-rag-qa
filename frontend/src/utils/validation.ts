/** 表单校验：手机号等常见字段 */

/** 中国大陆手机号：1 开头，第二位 3–9，共 11 位数字 */
export const CN_MOBILE_RE = /^1[3-9]\d{9}$/;

export function isCnMobile(value: string): boolean {
  return CN_MOBILE_RE.test(String(value || "").trim());
}

/** 字段 key/label 是否像电话 */
export function looksLikePhoneField(key: string, label = ""): boolean {
  const s = `${key} ${label}`.toLowerCase();
  return /phone|mobile|tel|电话|手机|联系方式/.test(s);
}

export function phoneError(value: string, required = false): string | null {
  const v = String(value || "").trim();
  if (!v) return required ? "请填写手机号" : null;
  if (!isCnMobile(v)) return "请输入有效的 11 位手机号";
  return null;
}

/** 联系方式：手机 11 位，或至少 5 位的微信号等 */
export function contactError(value: string): string | null {
  const v = String(value || "").trim();
  if (!v) return "请填写联系方式";
  if (/^\d+$/.test(v)) {
    if (!isCnMobile(v)) return "手机号须为 11 位有效号码";
    return null;
  }
  if (v.length < 5) return "联系方式过短";
  return null;
}
