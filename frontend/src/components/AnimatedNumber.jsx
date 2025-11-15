import { useEffect, useRef, useState } from "react";

function AnimatedNumber({ value, format = (val) => val, duration = 900, className = "value" }) {
  const [displayValue, setDisplayValue] = useState(value);
  const previous = useRef(value);

  useEffect(() => {
    const startValue = previous.current;
    const delta = value - startValue;
    let start;
    let frame;

    const animate = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      setDisplayValue(startValue + delta * progress);
      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      } else {
        previous.current = value;
      }
    };

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return <span className={className}>{format(displayValue)}</span>;
}

export default AnimatedNumber;
