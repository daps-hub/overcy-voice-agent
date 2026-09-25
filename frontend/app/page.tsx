"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function Home() {
  const [status, setStatus] = useState("Ready");
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [lastAction, setLastAction] = useState<string | null>(
    null
  );

  const sessionIdRef = useRef<string>(
    crypto.randomUUID()
  );

  const mediaRecorderRef =
    useRef<MediaRecorder | null>(null);

  const streamRef =
    useRef<MediaStream | null>(null);

  const audioChunksRef =
    useRef<Blob[]>([]);
  const websocketRef =
  useRef<WebSocket | null>(null);
 const peerConnectionRef =
  useRef<RTCPeerConnection | null>(null);

const realtimeDataChannelRef =
  useRef<RTCDataChannel | null>(null);

const realtimeStreamRef =
  useRef<MediaStream | null>(null);

const realtimeAudioRef =
  useRef<HTMLAudioElement | null>(null);

const realtimeTranscriptItemsRef =
  useRef<Set<string>>(new Set());

useEffect(() => {
  const websocket = new WebSocket(
    "ws://127.0.0.1:8000/ws/voice"
  );

  websocketRef.current = websocket;

  websocket.onopen = () => {
  console.log(
    "Voice WebSocket connected"
  );
};
  websocket.onmessage = (event) => {
    console.log(
      "WebSocket message:",
      event.data
    );
  };

 websocket.onerror = () => {
  console.log(
    "WebSocket encountered an error"
  );
};

  websocket.onclose = (event) => {
  console.log(
    "Voice WebSocket disconnected",
    {
      code: event.code,
      reason: event.reason,
      clean: event.wasClean,
    }
  );
};
  return () => {
    websocket.close();
  };
}, []);

  const startRealtimeConversation = async () => {
  try {
    console.log("Starting OpenAI Realtime...");

    realtimeTranscriptItemsRef.current.clear();

    // 1. Get temporary credential from FastAPI
    const tokenResponse = await fetch(
      "http://127.0.0.1:8000/api/realtime/token"
    );

    if (!tokenResponse.ok) {
      throw new Error(
        "Failed to get Realtime token"
      );
    }

    const tokenData =
      await tokenResponse.json();

    const ephemeralKey =
      tokenData.value;

    if (!ephemeralKey) {
      throw new Error(
        "Realtime token missing"
      );
    }

    // 2. Create WebRTC connection
    const pc = new RTCPeerConnection();

    peerConnectionRef.current = pc;

    // 3. Create audio element for AI speech
    const audio = new Audio();

    audio.autoplay = true;

    realtimeAudioRef.current = audio;

    pc.ontrack = (event) => {
      console.log(
        "Realtime AI audio received"
      );

      audio.srcObject =
        event.streams[0];
    };

    // 4. Get microphone
    const stream =
      await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

    realtimeStreamRef.current =
      stream;

    stream.getTracks().forEach(
      (track) => {
        pc.addTrack(
          track,
          stream
        );
      }
    );

    // 5. Data channel for Realtime events
    const dataChannel =
      pc.createDataChannel(
        "oai-events"
      );

    realtimeDataChannelRef.current =
      dataChannel;

    dataChannel.onopen = () => {
      console.log(
        "OpenAI Realtime data channel OPEN"
      );
    };

    dataChannel.onmessage = async (event) => {
  const realtimeEvent = JSON.parse(event.data);

  console.log(
    "Realtime event:",
    realtimeEvent
  );

  // Realtime user transcript.
  // OpenAI emits this after each user audio turn when input
  // transcription is enabled for the Realtime session.
  if (
    realtimeEvent.type ===
    "conversation.item.input_audio_transcription.completed"
  ) {
    const transcript =
      realtimeEvent.transcript?.trim();

    const transcriptKey =
      `user:${realtimeEvent.item_id}`;

    if (
      transcript &&
      !realtimeTranscriptItemsRef.current.has(
        transcriptKey
      )
    ) {
      realtimeTranscriptItemsRef.current.add(
        transcriptKey
      );

      setMessages((previous) => [
        ...previous,
        {
          role: "user",
          text: transcript,
        },
      ]);
    }
  }

  // Realtime assistant transcript.
  // Use the completed audio transcript so each AI turn is
  // added to the chat only once.
  if (
    realtimeEvent.type ===
    "response.output_audio_transcript.done"
  ) {
    const transcript =
      realtimeEvent.transcript?.trim();

    const transcriptKey =
      `assistant:${realtimeEvent.item_id}`;

    if (
      transcript &&
      !realtimeTranscriptItemsRef.current.has(
        transcriptKey
      )
    ) {
      realtimeTranscriptItemsRef.current.add(
        transcriptKey
      );

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: transcript,
        },
      ]);
    }
  }

  if (
    realtimeEvent.type ===
    "response.function_call_arguments.done"
  ) {
    console.log(
      "REALTIME TOOL CALL:",
      realtimeEvent.name,
      realtimeEvent.arguments
    );

    try {
      const toolResponse = await fetch(
        "http://127.0.0.1:8000/api/realtime/tool",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: realtimeEvent.name,
            arguments: JSON.parse(
              realtimeEvent.arguments
            ),
          }),
        }
      );

      const toolResult =
        await toolResponse.json();

      console.log(
        "REALTIME TOOL RESULT:",
        toolResult
      );

      // Keep the Realtime UI banner in sync with the actual tool result.
      if (realtimeEvent.name === "create_lead") {
        if (toolResult?.duplicate) {
          setLastAction("✓ Existing lead found");
        } else {
          setLastAction("✓ Lead captured");
        }
      }

      else if (realtimeEvent.name === "create_appointment") {
        if (toolResult?.success === false) {
          setLastAction("⚠ Appointment not scheduled");
        } else if (toolResult?.duplicate) {
          setLastAction("✓ Existing appointment found");
        } else {
          setLastAction("✓ Appointment scheduled");
        }
      }

      else if (
        realtimeEvent.name === "create_lead_and_appointment"
      ) {
        // Realtime endpoint may wrap the business result.
        // Normalize it first, then trust the appointment result itself.
        const businessResult =
          toolResult?.result ?? toolResult;

        const appointment =
          businessResult?.appointment;

        const appointmentSucceeded =
          appointment?.success === true;

        const leadDuplicate =
          businessResult?.lead?.duplicate;

        const appointmentDuplicate =
          appointment?.duplicate;

        if (!appointmentSucceeded) {
          setLastAction(
            "✓ Lead captured • ⚠ Appointment not scheduled"
          );
        } else if (
          leadDuplicate &&
          appointmentDuplicate
        ) {
          setLastAction(
            "✓ Existing customer • Existing appointment found"
          );
        } else if (leadDuplicate) {
          setLastAction(
            "✓ Existing customer • New appointment scheduled"
          );
        } else if (appointmentDuplicate) {
          setLastAction(
            "✓ Lead captured • Existing appointment found"
          );
        } else {
          setLastAction(
            "✓ Lead captured • Appointment scheduled"
          );
        }
      }

      dataChannel.send(
        JSON.stringify({
          type: "conversation.item.create",
          item: {
            type: "function_call_output",
            call_id: realtimeEvent.call_id,
            output: JSON.stringify(
              toolResult
            ),
          },
        })
      );

      dataChannel.send(
        JSON.stringify({
          type: "response.create",
        })
      );

    } catch (error) {
      console.error(
        "Realtime tool execution error:",
        error
      );
    }
  }
};

    dataChannel.onclose = () => {
      console.log(
        "OpenAI Realtime data channel CLOSED"
      );
    };

    // 6. Create SDP offer
    const offer =
      await pc.createOffer();

    await pc.setLocalDescription(
      offer
    );

    // 7. Send SDP to OpenAI
    const sdpResponse = await fetch(
      "https://api.openai.com/v1/realtime/calls",
      {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization:
            `Bearer ${ephemeralKey}`,
          "Content-Type":
            "application/sdp",
        },
      }
    );

    if (!sdpResponse.ok) {
      const errorText =
        await sdpResponse.text();

      throw new Error(
        `Realtime connection failed: ${errorText}`
      );
    }

    // 8. Receive SDP answer
    const answerSdp =
      await sdpResponse.text();

    await pc.setRemoteDescription({
      type: "answer",
      sdp: answerSdp,
    });

    console.log(
      "OPENAI REALTIME CONNECTED"
    );

  } catch (error) {
    console.error(
      "Realtime error:",
      error
    );
  }
};

  const stopRealtimeConversation = () => {
  console.log("Stopping OpenAI Realtime...");

  // Close the OpenAI data channel
  if (realtimeDataChannelRef.current) {
    realtimeDataChannelRef.current.close();
    realtimeDataChannelRef.current = null;
  }

  // Close the WebRTC connection
  if (peerConnectionRef.current) {
    peerConnectionRef.current.close();
    peerConnectionRef.current = null;
  }

  // Stop microphone access
  if (realtimeStreamRef.current) {
    realtimeStreamRef.current
      .getTracks()
      .forEach((track) => track.stop());

    realtimeStreamRef.current = null;
  }

  // Stop AI audio playback
  if (realtimeAudioRef.current) {
    realtimeAudioRef.current.pause();
    realtimeAudioRef.current.srcObject = null;
    realtimeAudioRef.current = null;
  }

  console.log("OPENAI REALTIME STOPPED");
};

  async function startRecording() {
    try {
      const stream =
        await navigator.mediaDevices.getUserMedia({
          audio: true,
        });

      streamRef.current = stream;
      audioChunksRef.current = [];

      const mediaRecorder =
        new MediaRecorder(stream);

      mediaRecorderRef.current = mediaRecorder;

     mediaRecorder.ondataavailable = async (event) => {
  console.log(
    "Audio chunk created:",
    event.data.size,
    "bytes"
  );

  if (event.data.size > 0) {
    audioChunksRef.current.push(
      event.data
    );

    const websocket =
      websocketRef.current;

    console.log(
      "WebSocket state:",
      websocket?.readyState
    );

    if (
      websocket &&
      websocket.readyState === WebSocket.OPEN
    ) {
      const audioBuffer =
        await event.data.arrayBuffer();

      websocket.send(audioBuffer);

      console.log(
        "Audio chunk sent:",
        audioBuffer.byteLength,
        "bytes"
      );
    }
  }
};

      mediaRecorder.onstop = async () => {
        try {
          setStatus("Thinking...");
          setLastAction(null);

          const audioBlob = new Blob(
            audioChunksRef.current,
            {
              type:
                mediaRecorder.mimeType ||
                "audio/webm",
            }
          );

          const formData = new FormData();

          formData.append(
            "audio",
            audioBlob,
            "browser-recording.webm"
          );

          formData.append(
            "session_id",
            sessionIdRef.current
          );

          // STEP 1:
          // Send voice to the AI agent ONCE.
          const conversationResponse =
            await fetch(
              "http://127.0.0.1:8000/api/voice/conversation",
              {
                method: "POST",
                body: formData,
              }
            );

          if (!conversationResponse.ok) {
            const errorText =
              await conversationResponse.text();

            console.error(
              "Conversation API error:",
              errorText
            );

            throw new Error(
              `Conversation API returned ${conversationResponse.status}`
            );
          }

          const data =
            await conversationResponse.json();

          // STEP 2:
          // Display user transcript + AI response.
          setMessages((previous) => [
            ...previous,
            {
              role: "user",
              text: data.transcript,
            },
            {
              role: "assistant",
              text: data.response,
            },
          ]);

          // STEP 3:
          // Display the business action.
          if (data.tool_called === "create_lead") {
  if (data.tool_result?.duplicate) {
    setLastAction(
      "✓ Existing lead found"
    );
  } else {
    setLastAction(
      "✓ Lead captured"
    );
  }
}

else if (
  data.tool_called === "create_appointment"
) {
  if (data.tool_result?.success === false) {
    setLastAction(
      "⚠ Appointment not scheduled"
    );
  } else if (data.tool_result?.duplicate) {
    setLastAction(
      "✓ Existing appointment found"
    );
  } else {
    setLastAction(
      "✓ Appointment scheduled"
    );
  }
}

  else if (
    data.tool_called === "create_lead_and_appointment"
  ) {
    const bookingSucceeded =
      data.tool_result?.success === true;

    const leadDuplicate =
      data.tool_result?.lead?.duplicate;

    const appointmentDuplicate =
      data.tool_result?.appointment?.duplicate;

    if (!bookingSucceeded) {
      setLastAction(
        "✓ Lead captured • ⚠ Appointment not scheduled"
      );
    }

    else if (
      leadDuplicate &&
      appointmentDuplicate
    ) {
      setLastAction(
        "✓ Existing customer • Existing appointment found"
      );
    }

    else if (leadDuplicate) {
      setLastAction(
        "✓ Existing customer • New appointment scheduled"
      );
    }

    else if (appointmentDuplicate) {
      setLastAction(
        "✓ Lead captured • Existing appointment found"
      );
    }

    else {
      setLastAction(
        "✓ Lead captured • Appointment scheduled"
      );
    }
  }

          // STEP 4:
          // Convert ONLY the AI response to speech.
          setStatus("AI is speaking...");

          const ttsResponse = await fetch(
            "http://127.0.0.1:8000/api/tts",
            {
              method: "POST",
              headers: {
                "Content-Type":
                  "application/json",
              },
              body: JSON.stringify({
                text: data.response,
              }),
            }
          );

          if (!ttsResponse.ok) {
            const errorText =
              await ttsResponse.text();

            console.error(
              "TTS API error:",
              errorText
            );

            throw new Error(
              `TTS API returned ${ttsResponse.status}`
            );
          }

          const responseAudioBlob =
            await ttsResponse.blob();

          const audioUrl =
            URL.createObjectURL(
              responseAudioBlob
            );

          const audio = new Audio(audioUrl);

          audio.onended = () => {
            setStatus("Ready");

            URL.revokeObjectURL(
              audioUrl
            );
          };

          await audio.play();
        } catch (error) {
          console.error(error);

          setStatus(
            "Something went wrong"
          );
        }
      };

      mediaRecorder.start(250);

      setIsRecording(true);
      setStatus("Listening...");
    } catch (error) {
      console.error(error);

      setStatus(
        "Microphone access denied"
      );
    }
  }

  function stopRecording() {
    const recorder =
      mediaRecorderRef.current;

    if (
      recorder &&
      recorder.state !== "inactive"
    ) {
      recorder.stop();
    }

    streamRef.current
      ?.getTracks()
      .forEach((track) => {
        track.stop();
      });

    setIsRecording(false);
    setStatus("Processing...");
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6">
      <div className="mx-auto w-full max-w-2xl py-10">

        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400 mb-5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            AI Agent Online
          </div>

          <h1 className="text-4xl font-bold">
            AI Voice Assistant
          </h1>

          <p className="mt-3 text-slate-400">
            Speak naturally. The AI can answer
            questions, capture leads, and schedule
            appointments.
          </p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">

          <div className="flex flex-col items-center">

            <div
              className={`mb-6 flex h-28 w-28 items-center justify-center rounded-full ${
                isRecording
                  ? "bg-red-500/20 animate-pulse"
                  : "bg-blue-500/10"
              }`}
            >
              <div
                className={`flex h-20 w-20 items-center justify-center rounded-full text-4xl shadow-lg ${
                  isRecording
                    ? "bg-red-600"
                    : "bg-blue-600"
                }`}
              >
                🎙️
              </div>
            </div>

            <p className="text-sm uppercase tracking-widest text-slate-500">
              Status
            </p>

            <p className="mt-2 text-xl font-semibold">
              {status}
            </p>

           {!isRecording ? (
            <>
              <button
                onClick={startRecording}
                disabled={isRecording}
                className="
                  mx-auto w-full max-w-xl rounded-xl
                  bg-gradient-to-b
                  from-emerald-200 via-emerald-300 to-emerald-500
                  px-5 py-3
                  text-base font-bold text-slate-900
                  border border-emerald-100
                  shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(16,185,129,0.25)]
                  hover:from-emerald-100 hover:via-emerald-200 hover:to-emerald-400
                  active:scale-[0.99]
                  transition-all duration-150
                  disabled:opacity-50
                "
              >
                Start Conversation
              </button>

              <button
                onClick={startRealtimeConversation}
                className="mt-3 mx-auto w-full max-w-xl rounded-xl
                  bg-gradient-to-b from-sky-200 via-sky-300 to-blue-500
                  px-5 py-3 text-base font-bold text-slate-900
                  border border-sky-100
                  shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(14,165,233,0.25)]
                  hover:from-sky-100 hover:via-sky-200 hover:to-blue-400
                  active:scale-[0.99] transition-all duration-150"
              >
                ▶ Start Realtime Voice
              </button>

              <button
              onClick={stopRealtimeConversation}
              className="mt-3 mx-auto w-full max-w-xl rounded-xl
                  bg-gradient-to-b from-rose-200 via-red-300 to-red-500
                  px-5 py-3 text-base font-bold text-slate-900
                  border border-rose-100
                  shadow-[inset_0_2px_2px_rgba(255,255,255,0.85),0_5px_14px_rgba(239,68,68,0.25)]
                  hover:from-rose-100 hover:via-red-200 hover:to-red-400
                  active:scale-[0.99] transition-all duration-150"
            >
              ■ Stop Realtime Voice
            </button>
            </>
          ) : (
            <button
              onClick={stopRecording}
              className="w-full rounded-xl bg-red-600 px-6 py-4 font-semibold text-white"
            >
              Stop & Send
            </button>
          )}

          </div>
        </div>

        {/* Conversation transcript */}
        <div className="mt-6 rounded-3xl border border-slate-800 bg-slate-900 p-6">

          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              Conversation
            </h2>

            <span className="text-xs text-slate-500">
              Live transcript
            </span>
          </div>

          {messages.length === 0 ? (
            <p className="mt-6 text-center text-sm text-slate-500">
              Your conversation will appear here.
            </p>
          ) : (
            <div className="mt-6 space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={
                    message.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-800 text-slate-100"
                    }`}
                  >
                    <div className="mb-1 text-xs font-semibold opacity-70">
                      {message.role === "user"
                        ? "You"
                        : "AI Assistant"}
                    </div>

                    <p>{message.text}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {lastAction && (
            <div className="mt-5 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
              {lastAction}
            </div>
          )}

        </div>

        <div className="mt-6 grid grid-cols-3 gap-3 text-center">

          <div className="rounded-xl bg-slate-900 p-4">
            <div>🧠</div>
            <div className="mt-2 text-xs text-slate-400">
              AI Agent
            </div>
          </div>

          <div className="rounded-xl bg-slate-900 p-4">
            <div>👤</div>
            <div className="mt-2 text-xs text-slate-400">
              Lead Capture
            </div>
          </div>

          <div className="rounded-xl bg-slate-900 p-4">
            <div>📅</div>
            <div className="mt-2 text-xs text-slate-400">
              Scheduling
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}