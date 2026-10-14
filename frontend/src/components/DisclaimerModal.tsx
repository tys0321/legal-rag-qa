// 首次登录免责声明弹窗（必须确认）

interface Props {
  onAck: () => void;
}

export default function DisclaimerModal({ onAck }: Props) {
  return (
    <div className="modal-mask">
      <div className="modal-card">
        <h2>服务声明与风险提示</h2>
        <p>
          本系统基于 AI 与法律法规知识库生成内容，<strong>仅供一般性法律知识参考</strong>
          ，不构成正式法律意见或律师服务。
        </p>
        <ul>
          <li>涉及人身安全、刑事指控等情形，请立即报警或咨询执业律师。</li>
          <li>重大财产争议请以专业律师意见为准。</li>
          <li>法条引用可能存在滞后或遗漏，请核对现行有效文本。</li>
        </ul>
        <button className="btn-primary" type="button" onClick={onAck}>
          我已阅读并理解，继续使用
        </button>
      </div>
    </div>
  );
}
