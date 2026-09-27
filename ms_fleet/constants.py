"""Names shared by the fleet modules: trip states, billing modes, stop purposes and roles."""

DRAFT = "مسودة"
PENDING = "بانتظار الاعتماد"
ASSIGNED = "مسندة"
ACCEPTED = "مقبولة"
IN_PROGRESS = "جارية"
FINISHED = "منتهية"
APPROVED = "معتمدة للصرف"
INVOICED = "مفوترة"
DECLINED = "مرفوضة من السواق"
CANCELLED = "ملغاة"

# The driver's current work, and the states in which a trip can still be (re)assigned.
ACTIVE_STATES = (ASSIGNED, ACCEPTED, IN_PROGRESS)
ASSIGNABLE_STATES = (PENDING, ASSIGNED, DECLINED, ACCEPTED)

BY_KM = "بالكيلو"
BY_DAY = "باليومية"

LOADING = "تحميل"
DELIVERY = "تنزيل"
PASSENGERS = "ركاب"
# A photo is taken where goods change hands; a delivery also needs the receiver's confirmation.
PHOTO_PURPOSES = (LOADING, DELIVERY)
CONFIRM_PURPOSES = (DELIVERY,)

COMPANY_OWNED = "شركة"
EXTERNAL = "خارجي"

VIA_ACCOUNT = "حساب المستلم"
VIA_CODE = "كود المستلم"
VIA_OVERRIDE = "استثناء"

DISTANCE_MAP = "الخريطة"
DISTANCE_MANUAL = "يدوي"

FLEET_MANAGER = "Fleet Manager"
FLEET_REQUESTER = "Fleet Requester"
FLEET_DRIVER = "Fleet Driver"
RELAY_CLIENT = "Fleet Relay Client"

PUSH_PROJECT = "ms_fleet"
MAX_CODE_ATTEMPTS = 5
