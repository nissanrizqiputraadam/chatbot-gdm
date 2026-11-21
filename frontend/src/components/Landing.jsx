import hands from "../assets/landing-hands.png";
import crowd from "../assets/landing-crowd.png";
import "./Landing.css";

export default function Landing({ onAsk }) {
  return (
    <div className="landing-page">
      <header className="landing-nav">
        <a href="#home" className="landing-logo" aria-label="GDM beranda">GDM</a>
      </header>

      <main>
        <section className="landing-hero" id="home">
          <div className="landing-stage">
            <div className="landing-hands" aria-hidden="true">
              <img src={hands} alt="" />
            </div>
            <div className="landing-copy">
              <h1>Ketika sesuatu terasa aneh, tanyakan ke GDM</h1>
              <p>Kami membantu orang untuk mencari tahu tentang diabetes dan menjawab penanganan yang tepat</p>
              <button className="landing-cta" onClick={onAsk}>Tanyakan kami</button>
            </div>
            <div className="landing-crowd" aria-hidden="true">
              <img src={crowd} alt="" />
            </div>
          </div>
        </section>

        <section className="landing-help">
          <div className="landing-stage landing-help-stage">
            <h2>Bagaimana cara kami membantu:</h2>
            <div className="landing-help-body">
              <h3>Gunakan chatbot kami untuk membantu mengenai apa yang harus dilakukan</h3>
              <svg className="help-illustration" viewBox="0 0 165 125" aria-hidden="true">
                <rect className="illustration-panel" x="52" y="8" width="70" height="75" />
                <rect className="illustration-message" x="80" y="22" width="68" height="18" />
                <rect className="illustration-message" x="80" y="48" width="68" height="18" />
                <rect className="illustration-paper" x="22" y="14" width="40" height="48" rx="3" />
                <path className="illustration-paper-lines" d="M28 30h28M28 38h28M28 46h22" />
                <circle className="illustration-question" cx="38" cy="8" r="7" />
                <text className="illustration-question-text" x="38" y="12">?</text>
                <path className="illustration-person" d="M0 125q4-40 40-53h42q14 10 18 53Z" />
                <ellipse className="illustration-hair" cx="60" cy="62" rx="20" ry="22" />
                <path className="illustration-skin" d="m88 84 12-18 8 6-10 22Zm8-24q12-8 14 4l-6 10-8-4Z" />
                <path className="illustration-hand" d="m96 60q12-8 14 4l-6 10-8-4Z" />
                <rect className="illustration-calculator" x="112" y="88" width="26" height="36" rx="3" />
                <rect className="illustration-calculator-screen" x="118" y="93" width="8" height="8" />
                <path className="illustration-plus" d="M122 94.5v5m-2.5-2.5h5" />
                <g className="illustration-calculator-buttons">
                  <circle cx="119" cy="108" r="1.2" /><circle cx="124" cy="108" r="1.2" /><circle cx="129" cy="108" r="1.2" />
                  <circle cx="119" cy="113" r="1.2" /><circle cx="124" cy="113" r="1.2" /><circle cx="129" cy="113" r="1.2" />
                  <circle cx="119" cy="118" r="1.2" /><circle cx="124" cy="118" r="1.2" /><circle cx="129" cy="118" r="1.2" />
                </g>
                <circle className="illustration-pill" cx="152" cy="82" r="8" />
                <rect className="illustration-pill-mark" x="147" y="80" width="10" height="4" rx="2" />
              </svg>
              <p>
                Situasimu memiliki kondisi yang unik dan spesifik. Chatbot kami akan mengajukan pertanyaan dan membantu mencari tahu apa yang sedang terjadi berdasarkan jawabanmu. Tidak perlu lagi menebak-nebak atau mengisi informasi yang belum jelas. Rasanya seperti berbicara dengan temanmu yang kebetulan berprofesi sebagai dokter.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
