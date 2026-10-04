"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Appointment = {
  id: number;
  lead_id: number | null;
  name: string | null;
  phone: string | null;
  email: string | null;
  reason: string | null;
  appointment_date: string;
  appointment_time: string;
  status: string;
  created_at: string | null;
};

const API_URL = "http://127.0.0.1:8000";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function dateKey(year: number, month: number, day: number) {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(
    day
  ).padStart(2, "0")}`;
}

function formatTime(value: string) {
  if (!value) return "—";

  const [hourText, minuteText = "00"] = value.split(":");
  const hour = Number(hourText);

  if (Number.isNaN(hour)) return value;

  const suffix = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;

  return `${displayHour}:${minuteText} ${suffix}`;
}

function formatDate(value: string) {
  if (!value) return "—";

  const [year, month, day] = value.split("-").map(Number);

  if (!year || !month || !day) return value;

  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function createdAtValue(value: string | null) {
  if (!value) return 0;

  const parsed = new Date(value.replace(" ", "T")).getTime();

  return Number.isNaN(parsed) ? 0 : parsed;
}

export default function CalendarPage() {
  const today = new Date();

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [selectedAppointment, setSelectedAppointment] =
    useState<Appointment | null>(null);

  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [latestBooking, setLatestBooking] =
    useState<Appointment | null>(null);

  const [newBookingCount, setNewBookingCount] = useState(0);

  const knownAppointmentIdsRef = useRef<Set<number>>(new Set());
  const initialLoadCompleteRef = useRef(false);

  async function loadAppointments() {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/appointments`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Unable to load appointments.");
      }

      const data = await response.json();

      const loadedAppointments: Appointment[] =
        data.appointments ?? [];

      const sortedByCreated = loadedAppointments
      .filter(
        (appointment) =>
          appointment.status?.toLowerCase() === "scheduled"
      )
      .sort(
        (a, b) =>
          createdAtValue(b.created_at) -
          createdAtValue(a.created_at)
      );

      if (!initialLoadCompleteRef.current) {
        loadedAppointments.forEach((appointment) => {
          knownAppointmentIdsRef.current.add(appointment.id);
        });

        if (sortedByCreated.length > 0) {
          setLatestBooking(sortedByCreated[0]);
        }

        initialLoadCompleteRef.current = true;
      } else {
        const newAppointments = loadedAppointments.filter(
          (appointment) =>
            !knownAppointmentIdsRef.current.has(appointment.id)
        );

        if (newAppointments.length > 0) {
          const newestNewBooking = [...newAppointments].sort(
            (a, b) =>
              createdAtValue(b.created_at) -
              createdAtValue(a.created_at)
          )[0];

          setNewBookingCount(newAppointments.length);
          setLatestBooking(newestNewBooking);
        }

        loadedAppointments.forEach((appointment) => {
          knownAppointmentIdsRef.current.add(appointment.id);
        });
      }
      
      setLatestBooking(
        sortedByCreated.length > 0
          ? sortedByCreated[0]
          : null
      );
      setSelectedAppointment((current) => {
  if (!current) return null;

  return (
    loadedAppointments.find(
      (appointment) => appointment.id === current.id
    ) ?? null
  );
});
      setAppointments(loadedAppointments);
    } catch (err) {
      console.error(err);

      setError(
        "Could not load appointments. Make sure the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAppointments();
  }, []);

  const appointmentsByDate = useMemo(() => {
    const grouped: Record<string, Appointment[]> = {};

   appointments.forEach((appointment) => {
  // Do not show cancelled appointments on the calendar.
  if (appointment.status?.toLowerCase() !== "scheduled") {
    return;
  }

  if (!grouped[appointment.appointment_date]) {
    grouped[appointment.appointment_date] = [];
  }

  grouped[appointment.appointment_date].push(appointment);
});

    Object.values(grouped).forEach((items) => {
      items.sort((a, b) =>
        a.appointment_time.localeCompare(b.appointment_time)
      );
    });

    return grouped;
  }, [appointments]);

  const monthAppointments = useMemo(() => {
    const prefix = `${currentYear}-${String(
      currentMonth + 1
    ).padStart(2, "0")}`;

    return appointments
      .filter((appointment) =>
        appointment.appointment_date.startsWith(prefix)
      )
      .sort((a, b) => {
        const dateCompare =
          a.appointment_date.localeCompare(
            b.appointment_date
          );

        if (dateCompare !== 0) {
          return dateCompare;
        }

        return a.appointment_time.localeCompare(
          b.appointment_time
        );
      });
  }, [appointments, currentYear, currentMonth]);

  const calendarDays = useMemo(() => {
    const firstDay = new Date(
      currentYear,
      currentMonth,
      1
    ).getDay();

    const daysInMonth = new Date(
      currentYear,
      currentMonth + 1,
      0
    ).getDate();

    const previousMonthDays = new Date(
      currentYear,
      currentMonth,
      0
    ).getDate();

    const cells: {
      day: number;
      monthOffset: number;
      date: string;
    }[] = [];

    for (let i = firstDay - 1; i >= 0; i--) {
      const day = previousMonthDays - i;

      const date = new Date(
        currentYear,
        currentMonth - 1,
        day
      );

      cells.push({
        day,
        monthOffset: -1,
        date: dateKey(
          date.getFullYear(),
          date.getMonth(),
          date.getDate()
        ),
      });
    }

    for (let day = 1; day <= daysInMonth; day++) {
      cells.push({
        day,
        monthOffset: 0,
        date: dateKey(
          currentYear,
          currentMonth,
          day
        ),
      });
    }

    let nextDay = 1;

    while (cells.length < 42) {
      const date = new Date(
        currentYear,
        currentMonth + 1,
        nextDay
      );

      cells.push({
        day: nextDay,
        monthOffset: 1,
        date: dateKey(
          date.getFullYear(),
          date.getMonth(),
          date.getDate()
        ),
      });

      nextDay++;
    }

    return cells;
  }, [currentYear, currentMonth]);

  function previousMonth() {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((year) => year - 1);
    } else {
      setCurrentMonth((month) => month - 1);
    }

    setSelectedAppointment(null);
  }

  function nextMonth() {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((year) => year + 1);
    } else {
      setCurrentMonth((month) => month + 1);
    }

    setSelectedAppointment(null);
  }

  function goToToday() {
    const now = new Date();

    setCurrentMonth(now.getMonth());
    setCurrentYear(now.getFullYear());
    setSelectedAppointment(null);
  }

  function viewBooking(appointment: Appointment) {
    const [year, month] =
      appointment.appointment_date
        .split("-")
        .map(Number);

    if (year && month) {
      setCurrentYear(year);
      setCurrentMonth(month - 1);
    }

    setSelectedAppointment(appointment);
    setNewBookingCount(0);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  const todayKey = dateKey(
    today.getFullYear(),
    today.getMonth(),
    today.getDate()
  );

  const scheduledCount = appointments.filter(
    (appointment) =>
      appointment.status?.toLowerCase() === "scheduled"
  ).length;

  const upcomingCount = appointments.filter(
    (appointment) => {
      if (
        appointment.status?.toLowerCase() !== "scheduled"
      ) {
        return false;
      }

      return appointment.appointment_date >= todayKey;
    }
  ).length;

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">

        {/* HEADER */}
        <div className="mb-7 flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 to-blue-600 text-2xl shadow-lg shadow-blue-500/20">
                📅
              </div>

              <div>
                <h1 className="text-3xl font-bold tracking-tight">
                  Appointment Calendar
                </h1>

                <p className="mt-1 text-sm text-slate-400">
                  Voice bookings and customer appointments
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <a
              href="/"
              className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-600 hover:bg-slate-800"
            >
              🎙️ Voice Agent
            </a>

            <button
              onClick={loadAppointments}
              disabled={loading}
              className="rounded-xl bg-gradient-to-b from-sky-400 via-sky-500 to-blue-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/20 transition hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading
                ? "↻ Refreshing..."
                : "↻ Refresh Bookings"}
            </button>
          </div>
        </div>

        {/* NEW / LATEST BOOKING */}
        {latestBooking && (
          <div
            className={`mb-6 overflow-hidden rounded-2xl border shadow-lg ${
              newBookingCount > 0
                ? "border-sky-400/50 bg-gradient-to-r from-sky-500/20 via-blue-500/15 to-slate-900 shadow-blue-500/10"
                : "border-slate-800 bg-slate-900"
            }`}
          >
            <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-4">
                <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-sky-500/15 text-2xl">
                  🔔

                  {newBookingCount > 0 && (
                    <span className="absolute -right-2 -top-2 flex h-6 min-w-6 items-center justify-center rounded-full bg-red-500 px-1.5 text-xs font-bold text-white shadow-lg">
                      {newBookingCount}
                    </span>
                  )}
                </div>

                <div>
                  <div
                    className={`text-xs font-bold uppercase tracking-wider ${
                      newBookingCount > 0
                        ? "text-sky-300"
                        : "text-slate-500"
                    }`}
                  >
                    {newBookingCount > 0
                      ? `${newBookingCount} New Booking${
                          newBookingCount === 1 ? "" : "s"
                        }`
                      : "Latest Booking"}
                  </div>

                  <div className="mt-1 text-lg font-bold text-white">
                    {latestBooking.name ?? "Customer"}
                  </div>

                  <div className="mt-1 text-sm text-slate-400">
                    {latestBooking.reason ||
                      "Appointment"}
                  </div>

                  <div className="mt-1 text-sm font-medium text-sky-300">
                    {formatDate(
                      latestBooking.appointment_date
                    )}
                    {" • "}
                    {formatTime(
                      latestBooking.appointment_time
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={() =>
                  viewBooking(latestBooking)
                }
                className="shrink-0 rounded-xl bg-gradient-to-b from-sky-400 via-sky-500 to-blue-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-blue-500/20 transition hover:brightness-110 active:scale-[0.98]"
              >
                View Booking →
              </button>
            </div>
          </div>
        )}

        {/* STATS */}
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Total Bookings"
            value={appointments.length}
            icon="📋"
          />

          <StatCard
            title="Scheduled"
            value={scheduledCount}
            icon="✓"
          />

          <StatCard
            title="Upcoming"
            value={upcomingCount}
            icon="⏱️"
          />

          <StatCard
            title="Customers"
            value={
              new Set(
                appointments
                  .map(
                    (appointment) =>
                      appointment.lead_id
                  )
                  .filter(Boolean)
              ).size
            }
            icon="👥"
          />
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-red-200">
            {error}
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-[1fr_380px]">

          {/* CALENDAR */}
          <section className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 shadow-2xl">

            <div className="flex flex-col gap-4 border-b border-slate-800 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-bold">
                  {MONTHS[currentMonth]}{" "}
                  {currentYear}
                </h2>

                <p className="mt-1 text-sm text-slate-400">
                  {monthAppointments.length} appointment
                  {monthAppointments.length === 1
                    ? ""
                    : "s"}{" "}
                  this month
                </p>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={previousMonth}
                  className="h-10 w-10 rounded-xl border border-slate-700 bg-slate-800 text-xl transition hover:bg-slate-700"
                  aria-label="Previous month"
                >
                  ‹
                </button>

                <button
                  onClick={goToToday}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-4 text-sm font-semibold transition hover:bg-slate-700"
                >
                  Today
                </button>

                <button
                  onClick={nextMonth}
                  className="h-10 w-10 rounded-xl border border-slate-700 bg-slate-800 text-xl transition hover:bg-slate-700"
                  aria-label="Next month"
                >
                  ›
                </button>
              </div>
            </div>

            <div className="grid grid-cols-7 border-b border-slate-800 bg-slate-950/50">
              {DAYS.map((day) => (
                <div
                  key={day}
                  className="px-2 py-3 text-center text-xs font-bold uppercase tracking-wider text-slate-500 sm:text-sm"
                >
                  {day}
                </div>
              ))}
            </div>

            {loading ? (
              <div className="flex min-h-[600px] items-center justify-center text-slate-400">
                Loading appointments...
              </div>
            ) : (
              <div className="grid grid-cols-7">
                {calendarDays.map((cell) => {
                  const dayAppointments =
                    appointmentsByDate[cell.date] ??
                    [];

                  const isToday =
                    cell.date === todayKey;

                  return (
                    <div
                      key={cell.date}
                      className={`min-h-[115px] border-b border-r border-slate-800 p-2 sm:min-h-[135px] ${
                        cell.monthOffset !== 0
                          ? "bg-slate-950/60"
                          : "bg-slate-900"
                      }`}
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <span
                          className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
                            isToday
                              ? "bg-blue-500 text-white shadow-lg shadow-blue-500/30"
                              : cell.monthOffset !==
                                0
                              ? "text-slate-600"
                              : "text-slate-300"
                          }`}
                        >
                          {cell.day}
                        </span>

                        {dayAppointments.length >
                          0 && (
                          <span className="rounded-full bg-sky-500/10 px-2 py-1 text-[10px] font-bold text-sky-300">
                            {
                              dayAppointments.length
                            }
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        {dayAppointments
                          .slice(0, 3)
                          .map(
                            (appointment) => (
                              <button
                                key={
                                  appointment.id
                                }
                                onClick={() =>
                                  setSelectedAppointment(
                                    appointment
                                  )
                                }
                                className={`block w-full truncate rounded-lg border px-2 py-1.5 text-left text-[11px] font-semibold transition sm:text-xs ${
                                  selectedAppointment?.id ===
                                  appointment.id
                                    ? "border-blue-400 bg-blue-500/30 text-white"
                                    : "border-sky-500/20 bg-sky-500/10 text-sky-200 hover:border-sky-400/50 hover:bg-sky-500/20"
                                }`}
                                title={`${
                                  appointment.name ??
                                  "Customer"
                                } - ${formatTime(
                                  appointment.appointment_time
                                )}`}
                              >
                                <span className="mr-1 text-sky-400">
                                  {formatTime(
                                    appointment.appointment_time
                                  )}
                                </span>

                                {appointment.name ??
                                  "Customer"}
                              </button>
                            )
                          )}

                        {dayAppointments.length >
                          3 && (
                          <div className="px-1 text-[10px] font-medium text-slate-500">
                            +
                            {dayAppointments.length -
                              3}{" "}
                            more
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* RIGHT PANEL */}
          <aside className="space-y-6">

            {/* DETAILS */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
              <h2 className="mb-5 text-lg font-bold">
                Appointment Details
              </h2>

              {!selectedAppointment ? (
                <div className="flex min-h-[320px] flex-col items-center justify-center text-center">
                  <div className="mb-4 text-5xl">
                    📆
                  </div>

                  <h3 className="font-semibold text-slate-300">
                    Select an appointment
                  </h3>

                  <p className="mt-2 max-w-[250px] text-sm leading-6 text-slate-500">
                    Click a booking on the
                    calendar or use View Booking
                    above.
                  </p>
                </div>
              ) : (
                <div>
                  <div className="mb-5 rounded-2xl border border-sky-500/20 bg-sky-500/10 p-4">
                    <div className="text-xs font-bold uppercase tracking-wider text-sky-400">
                      Customer
                    </div>

                    <div className="mt-1 text-xl font-bold">
                      {selectedAppointment.name ??
                        "Customer"}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <DetailRow
                      label="Service / Reason"
                      value={
                        selectedAppointment.reason ||
                        "Appointment"
                      }
                    />

                    <DetailRow
                      label="Date"
                      value={formatDate(
                        selectedAppointment.appointment_date
                      )}
                    />

                    <DetailRow
                      label="Time"
                      value={formatTime(
                        selectedAppointment.appointment_time
                      )}
                    />

                    <DetailRow
                      label="Phone"
                      value={
                        selectedAppointment.phone ||
                        "Not provided"
                      }
                    />

                    <DetailRow
                      label="Email"
                      value={
                        selectedAppointment.email ||
                        "Not provided"
                      }
                    />

                    <div className="border-t border-slate-800 pt-4">
                      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Status
                      </div>

                      <span className="inline-flex rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm font-bold capitalize text-emerald-300">
                        ●{" "}
                        {
                          selectedAppointment.status
                        }
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* MONTH BOOKINGS */}
            <section className="rounded-3xl border border-slate-800 bg-slate-900 p-5 shadow-xl">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="font-bold">
                    Month Bookings
                  </h2>

                  <p className="mt-1 text-xs text-slate-500">
                    {MONTHS[currentMonth]}{" "}
                    {currentYear}
                  </p>
                </div>

                <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-bold text-slate-300">
                  {monthAppointments.length}
                </span>
              </div>

              <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
                {monthAppointments.length ===
                0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-sm text-slate-500">
                    No appointments this month.
                  </div>
                ) : (
                  monthAppointments.map(
                    (appointment) => (
                      <button
                        key={appointment.id}
                        onClick={() =>
                          setSelectedAppointment(
                            appointment
                          )
                        }
                        className={`w-full rounded-xl border p-3 text-left transition ${
                          selectedAppointment?.id ===
                          appointment.id
                            ? "border-sky-500/50 bg-sky-500/10"
                            : "border-slate-800 bg-slate-950/60 hover:border-sky-500/30 hover:bg-slate-800"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-bold text-slate-200">
                              {appointment.name ??
                                "Customer"}
                            </div>

                            <div className="mt-1 truncate text-xs text-slate-500">
                              {appointment.reason ||
                                "Appointment"}
                            </div>
                          </div>

                          <div className="shrink-0 text-right">
                            <div className="text-xs font-bold text-sky-400">
                              {appointment.appointment_date.slice(
                                5
                              )}
                            </div>

                            <div className="mt-1 text-[11px] text-slate-500">
                              {formatTime(
                                appointment.appointment_time
                              )}
                            </div>
                          </div>
                        </div>
                      </button>
                    )
                  )
                )}
              </div>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: number;
  icon: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-lg">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-slate-500">
            {title}
          </div>

          <div className="mt-2 text-3xl font-bold text-white">
            {value}
          </div>
        </div>

        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-800 text-xl">
          {icon}
        </div>
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>

      <div className="break-words text-sm font-medium text-slate-200">
        {value}
      </div>
    </div>
  );
}